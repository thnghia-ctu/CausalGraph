from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = APP_DIR / "datasets"

STATUS_NEW = "new"
STATUS_INGESTING = "ingesting"
STATUS_CRAWLED = "crawled"
STATUS_READY = "ready"
STATUS_FAILED = "failed"

STATUS_LABELS = {
    STATUS_NEW: "Mới tạo",
    STATUS_INGESTING: "Đang xử lý",
    STATUS_CRAWLED: "Đã thu thập dữ liệu",
    STATUS_READY: "Sẵn sàng",
    STATUS_FAILED: "Lỗi",
}


URLS_FILENAME = "urls.txt"


@dataclass
class DatasetMeta:
    id: str
    name: str
    created_at: str
    source_url_count: int = 0
    status: str = STATUS_NEW
    error: str = ""
    stage_counts: dict[str, int] = field(default_factory=dict)
    last_distance_threshold: float | None = None
    last_min_sentence_count: int | None = None


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
    return DatasetMeta(**json.loads(path.read_text(encoding="utf-8")))


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
