import csv
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from string import Template
from typing import Any, Callable

from src.llm.base import LLMClient


FlattenFn = Callable[[list[dict[str, str]], list[dict[str, Any]]], list[dict[str, Any]]]

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```$")


def strip_json_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip()).strip()


def append_rows_to_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = path.exists()
    file_has_content = file_exists and path.stat().st_size > 0

    with path.open(
        mode="a",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        if not file_has_content:
            writer.writeheader()

        writer.writerows(rows)

        # Đẩy dữ liệu từ buffer Python xuống hệ điều hành.
        file.flush()


class BatchProcessor:
    def __init__(
        self,
        llm: LLMClient,
        items: list[dict[str, str]],
        prompt: Template,
        flatten_fn: FlattenFn,
        fieldnames: list[str],
        batch_size: int = 10,
        max_workers: int = 10,
        output_path: Path = Path("data/cache/results.csv"),
        max_batches: int | None = None,
    ) -> None:
        """items: mỗi phần tử là dict, tối thiểu có key "sentence".

        prompt: Template có placeholder $sentences, quyết định tác vụ đang chạy
        (gán nhãn causal, trích SPO, ...). flatten_fn nhận (batch, parsed_result)
        và trả về list các dict hàng CSV theo đúng schema riêng của tác vụ đó —
        fieldnames phải khớp với các key mà flatten_fn tạo ra.
        """
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")

        if max_batches is not None and max_batches <= 0:
            raise ValueError("max_batches must be greater than 0")

        self.llm = llm
        self.items = items
        self.prompt = prompt
        self.flatten_fn = flatten_fn
        self.fieldnames = fieldnames
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.output_path = output_path
        self.max_batches = max_batches

    def split_batches(self) -> list[list[dict[str, str]]]:
        batches = [
            self.items[i : i + self.batch_size]
            for i in range(0, len(self.items), self.batch_size)
        ]

        if self.max_batches is not None:
            batches = batches[: self.max_batches]

        return batches

    def build_prompt(self, batch: list[dict[str, str]]) -> str:
        sentences_json = json.dumps(
            [item["sentence"] for item in batch],
            ensure_ascii=False,
            indent=2,
        )

        return self.prompt.substitute(sentences=sentences_json)

    def process_batch(self, batch: list[dict[str, str]]) -> list[dict[str, Any]]:
        prompt = self.build_prompt(batch)
        raw = self.llm.generate(prompt)
        return json.loads(strip_json_fences(raw))

    def _save_error(
        self,
        *,
        batch_id: int,
        batch: list[dict[str, str]],
        error: Exception,
    ) -> None:
        print(f"Error processing batch {batch_id} ({len(batch)} sentences): {error}")

    def process_batches(self) -> list[dict[str, Any]]:
        """Chạy toàn bộ batch, ghi CSV theo từng batch, và trả về toàn bộ hàng
        đã flatten (thứ tự không đảm bảo theo thứ tự đầu vào, do chạy song song —
        nếu cần join theo đúng item, dựa vào một id field do flatten_fn giữ lại)."""
        batches = self.split_batches()
        all_rows: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[
                Future[list[dict[str, Any]]],
                tuple[int, list[dict[str, str]]],
            ] = {
                executor.submit(self.process_batch, batch): (batch_id, batch)
                for batch_id, batch in enumerate(batches)
            }

            for future in as_completed(futures):
                batch_id, batch = futures[future]

                try:
                    result = future.result()
                    rows = self.flatten_fn(batch, result)
                except Exception:
                    try:
                        result = self.process_batch(batch)  # thử lại đúng 1 lần
                        rows = self.flatten_fn(batch, result)
                    except Exception as retry_error:
                        self._save_error(batch_id=batch_id, batch=batch, error=retry_error)
                        continue

                # Dòng này chạy ở thread chính.
                append_rows_to_csv(path=self.output_path, rows=rows, fieldnames=self.fieldnames)

                all_rows.extend(rows)

        return all_rows
