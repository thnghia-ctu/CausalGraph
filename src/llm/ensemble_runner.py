import csv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any, Callable

from src.llm.base import LLMClient
from src.llm.batch_processor import BatchProcessor, FlattenFn, append_rows_to_csv


AgreementFn = Callable[[dict[str, list[dict[str, Any]]]], bool]

_CREDIT_EXHAUSTED_HINTS = ("insufficient", "credit", "quota", "payment required", "402")


def _looks_like_credit_exhausted(error: Exception) -> bool:
    text = str(error).lower()
    return any(hint in text for hint in _CREDIT_EXHAUSTED_HINTS)


def default_agreement_fn(agreement_fields: list[str]) -> AgreementFn:
    """So khớp mặc định: đúng 1 hàng/item/model, coi là đồng thuận khi giá trị
    các agreement_fields giống hệt nhau giữa các model. Phù hợp cho tác vụ
    phân loại (mỗi câu vào ra đúng 1 nhãn). Với tác vụ 1-nhiều (vd. SPO, một
    câu có thể tách thành nhiều bộ ba), cần truyền agreement_fn riêng."""

    def _check(rows_by_model: dict[str, list[dict[str, Any]]]) -> bool:
        signatures = set()
        for rows in rows_by_model.values():
            if len(rows) != 1:
                return False
            signatures.add(tuple(rows[0].get(f) for f in agreement_fields))
        return len(signatures) == 1

    return _check


@dataclass
class EnsembleRunner:
    """Chạy cùng một prompt trên N LLMClient khác nhau, gom kết quả theo item_id,
    tách thành consensus.csv (N model đồng thuận, dùng thẳng làm nhãn) và
    disagreement.csv (không đồng thuận hoặc có model lỗi/bỏ sót — ưu tiên đưa
    vào hàng đợi review/active learning thay vì cố gán tự động).

    Tách thành 2 bước độc lập:
    - fetch(): gọi API từng model, ghi {name}_raw.csv theo từng batch (tốn tiền,
      phụ thuộc mạng, có thể bị ngắt giữa chừng).
    - aggregate(): đọc lại {name}_raw.csv từ đĩa, so khớp, ghi consensus.csv/
      disagreement.csv (thuần cục bộ, không gọi API, chạy lại bao nhiêu lần
      cũng được, không phụ thuộc fetch() đã chạy trong cùng phiên hay chưa).

    run() = fetch() + aggregate(), tiện cho trường hợp chạy 1 lèo không cần tách.

    Dùng lại được cho bất kỳ tác vụ nào đã có sẵn (prompt, flatten_fn, fieldnames)
    theo đúng contract của BatchProcessor — không riêng cho causal detection.
    """

    clients: dict[str, LLMClient]
    items: list[dict[str, str]]
    prompt: Template
    flatten_fn: FlattenFn
    fieldnames: list[str]
    agreement_fields: list[str] = field(default_factory=list)
    agreement_fn: AgreementFn | None = None
    id_field: str = "item_id"
    output_dir: Path = Path("data/ensemble")
    batch_size: int = 10
    max_workers: int = 10
    max_batches: int | None = None
    rows_by_model: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if not self.agreement_fields and self.agreement_fn is None:
            raise ValueError("Cần agreement_fields hoặc agreement_fn để xác định đồng thuận.")

        for index, item in enumerate(self.items):
            item.setdefault(self.id_field, str(index))

        if self.agreement_fn is None:
            self.agreement_fn = default_agreement_fn(self.agreement_fields)

    def _raw_fieldnames(self) -> list[str]:
        return [self.id_field, *(f for f in self.fieldnames if f != self.id_field)]

    def _build_processors(self) -> dict[str, BatchProcessor]:
        return {
            name: BatchProcessor(
                llm=client,
                items=self.items,
                prompt=self.prompt,
                flatten_fn=self.flatten_fn,
                fieldnames=self._raw_fieldnames(),
                batch_size=self.batch_size,
                output_path=self.output_dir / f"{name}_raw.csv",
                max_batches=self.max_batches,
            )
            for name, client in self.clients.items()
        }

    def _process_batch_for_client(
        self,
        name: str,
        processor: BatchProcessor,
        batch_id: int,
        batch: list[dict[str, str]],
    ) -> tuple[list[dict[str, Any]], Exception | None]:
        try:
            result = processor.process_batch(batch)
            return self.flatten_fn(batch, result), None
        except Exception:
            try:
                result = processor.process_batch(batch)
                return self.flatten_fn(batch, result), None
            except Exception as retry_error:
                print(f"Error processing batch {batch_id} ({name}, {len(batch)} sentences): {retry_error}")
                return [], retry_error

    def _build_disagreement_row(
        self,
        item: dict[str, str],
        per_model: dict[str, list[dict[str, Any]]],
        reason: str,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            self.id_field: item[self.id_field],
            "sentence": item.get("sentence", ""),
            "reason": reason,
        }
        for name, rows in per_model.items():
            values = rows[0] if rows else {}
            for field_name in self.fieldnames:
                row[f"{name}_{field_name}"] = values.get(field_name)
        return row

    def fetch(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        processors = self._build_processors()
        batches = next(iter(processors.values())).split_batches()
        self.rows_by_model = {name: defaultdict(list) for name in self.clients}

        with ThreadPoolExecutor(max_workers=len(processors)) as executor:
            for batch_id, batch in enumerate(batches):
                futures = {
                    executor.submit(self._process_batch_for_client, name, processor, batch_id, batch): name
                    for name, processor in processors.items()
                }

                credit_exhausted = False
                for future in futures:
                    name = futures[future]
                    rows, error = future.result()

                    if rows:
                        append_rows_to_csv(processors[name].output_path, rows, fieldnames=processors[name].fieldnames)
                        for row in rows:
                            self.rows_by_model[name][str(row.get(self.id_field))].append(row)

                    if error is not None and _looks_like_credit_exhausted(error):
                        print(f"Dừng sớm: {name} có vẻ đã hết credit, ở batch {batch_id + 1}/{len(batches)}.")
                        credit_exhausted = True

                if credit_exhausted:
                    return self.rows_by_model

        return self.rows_by_model

    def _load_raw_from_disk(self) -> dict[str, dict[str, list[dict[str, Any]]]]:
        rows_by_model: dict[str, dict[str, list[dict[str, Any]]]] = {}

        for name in self.clients:
            raw_path = self.output_dir / f"{name}_raw.csv"
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

            if raw_path.exists():
                with raw_path.open(encoding="utf-8-sig", newline="") as f:
                    for row in csv.DictReader(f):
                        grouped[str(row.get(self.id_field))].append(row)

            rows_by_model[name] = grouped

        return rows_by_model

    def aggregate(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Đọc {name}_raw.csv từ đĩa (không dùng self.rows_by_model của fetch() nếu
        có, để đảm bảo kết quả luôn khớp với những gì thực sự đang nằm trên đĩa,
        kể cả khi fetch() chạy ở một phiên/process khác trước đó)."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        rows_by_model = self._load_raw_from_disk()

        consensus_rows: list[dict[str, Any]] = []
        disagreement_rows: list[dict[str, Any]] = []

        for item in self.items:
            item_id = item[self.id_field]
            per_model = {name: rows_by_model[name].get(item_id, []) for name in self.clients}

            if any(len(rows) == 0 for rows in per_model.values()):
                disagreement_rows.append(
                    self._build_disagreement_row(item, per_model, reason="missing_output")
                )
                continue

            if self.agreement_fn(per_model):
                first_model = next(iter(self.clients))
                consensus_rows.append({
                    self.id_field: item_id,
                    "sentence": item.get("sentence", ""),
                    "n_models": len(self.clients),
                    **per_model[first_model][0],
                })
            else:
                disagreement_rows.append(
                    self._build_disagreement_row(item, per_model, reason="disagreement")
                )

        append_rows_to_csv(
            self.output_dir / "consensus.csv",
            consensus_rows,
            fieldnames=[
                self.id_field, "sentence", "n_models",
                *(f for f in self.fieldnames if f not in (self.id_field, "sentence")),
            ],
        )

        disagreement_fieldnames = [self.id_field, "sentence", "reason"]
        disagreement_fieldnames.extend(
            f"{name}_{field_name}" for name in self.clients for field_name in self.fieldnames
        )
        append_rows_to_csv(
            self.output_dir / "disagreement.csv",
            disagreement_rows,
            fieldnames=disagreement_fieldnames,
        )

        return consensus_rows, disagreement_rows

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        self.fetch()
        return self.aggregate()
