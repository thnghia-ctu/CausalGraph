from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.constants.cons import (
    STATUS_FAILED,
    STATUS_INGESTING,
    STATUS_LABELS,
    STATUS_SUCCESS,
    STEP_NONE,
    STEP_CRAWL,
    STEP_CHUNK,
)

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"

STEP_PROGRESS = {
    STEP_NONE: 0,
    STEP_CRAWL: 50,
    STEP_CHUNK: 75,
}

URLS_FILENAME = "urls.txt"

@dataclass
class DatasetMeta:
    id: str
    name: str
    created_at: str
    source_url_count: int = 0
    status: str = STATUS_SUCCESS
    step: int = STEP_NONE
    error: str = ""
    stage_counts: dict[str, int] = field(default_factory=dict)
    last_distance_threshold: float | None = None
    last_min_sentence_count: int | None = None


def get_progress(meta: DatasetMeta) -> int:
    if get_status_label(meta) == "Sẵn sàng":
        return 100
    return STEP_PROGRESS.get(meta.step, 0)


def get_stage_progress(meta: DatasetMeta) -> dict[str, int | str]:
    """Return the active crawl/chunk progress without changing other callers."""
    dataset_path = dataset_dir(meta.id)
    current = 0
    goal = 0
    label = ""

    if meta.step == STEP_CRAWL:
        documents_path = dataset_path / "raw" / "documents.jsonl"
        current = sum(1 for line in documents_path.open(encoding="utf-8") if line.strip()) if documents_path.exists() else 0
        goal = meta.source_url_count
        label = "Thu thập dữ liệu"
    elif meta.step == STEP_CHUNK:
        documents_path = dataset_path / "raw" / "documents.jsonl"
        chunks_path = dataset_path / "chunks" / "chunks.jsonl"
        document_ids = set()
        if documents_path.exists():
            for line in documents_path.open(encoding="utf-8"):
                if line.strip():
                    document_ids.add(json.loads(line)["doc_id"])

        chunked_document_ids = set()
        if chunks_path.exists():
            for line in chunks_path.open(encoding="utf-8"):
                if line.strip():
                    chunked_document_ids.add(json.loads(line)["ref"]["doc"]["doc_id"])

        current = len(chunked_document_ids)
        goal = len(document_ids)
        label = "Phân đoạn dữ liệu"

    percentage = round(current / goal * 100) if goal else 0
    return {
        "current": current,
        "goal": goal,
        "percentage": min(percentage, 100),
        "label": label,
    }


def get_status_label(meta: DatasetMeta) -> str:
    if meta.step == STEP_NONE:
        return "Mới tạo"
    if meta.step <= STEP_CHUNK and meta.status == STATUS_FAILED:
        return "Lỗi dữ liệu"
    if (meta.step == STEP_CHUNK and meta.status == STATUS_SUCCESS) or meta.step > STEP_CHUNK:
        return "Sẵn sàng"
    if meta.step <= STEP_CHUNK and meta.status == STATUS_INGESTING:
        return "Đang xử lý"
    return STATUS_LABELS.get(meta.status, "Không xác định")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "dataset"


def dataset_dir(dataset_id: str) -> Path:
    return DATASETS_DIR / dataset_id


def _meta_path(dataset_id: str) -> Path:
    return dataset_dir(dataset_id) / "meta.json"


def _urls_path(dataset_id: str) -> Path:
    return dataset_dir(dataset_id) / URLS_FILENAME


def create_dataset(name: str, source_urls: list[str]) -> DatasetMeta:
    dataset_id = f"{_slugify(name)}-{uuid.uuid4().hex[:8]}"
    dataset_dir(dataset_id).mkdir(parents=True, exist_ok=True)

    if source_urls:
        _urls_path(dataset_id).write_text("\n".join(source_urls) + "\n", encoding="utf-8")

    meta = DatasetMeta(
        id=dataset_id,
        name=name,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_url_count=len(source_urls),
    )
    save_meta(meta)
    return meta


def load_source_urls(dataset_id: str) -> list[str]:
    path = _urls_path(dataset_id)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_meta(meta: DatasetMeta) -> None:
    _meta_path(meta.id).write_text(
        json.dumps(asdict(meta), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_meta(dataset_id: str) -> DatasetMeta | None:
    path = _meta_path(dataset_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("status", STATUS_SUCCESS)
    data.setdefault("step", STEP_NONE)
    return DatasetMeta(**data)


def list_datasets() -> list[DatasetMeta]:
    if not DATASETS_DIR.exists():
        return []
    metas = [
        load_meta(entry.name)
        for entry in DATASETS_DIR.iterdir()
        if entry.is_dir()
    ]
    valid = [meta for meta in metas if meta is not None]
    return sorted(valid, key=lambda meta: meta.created_at, reverse=True)


def delete_dataset(dataset_id: str) -> None:
    import shutil

    path = dataset_dir(dataset_id)
    if path.exists():
        shutil.rmtree(path)
