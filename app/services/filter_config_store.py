from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from configs.config import CHUNK_FILTER_THRESHOLD, KNOWLEDGE_BASE_PATH
from src.utils.helpers import load_xlsx

from app.services.dataset_store import dataset_dir

FILTER_CONFIG_FILENAME = "knowledge_base.json"


class FilterConfig(TypedDict):
    lexicon: list[str]
    query: list[str]
    threshold: float


def count_records(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def get_filter_progress(dataset_id: str) -> dict[str, int | float]:
    chunks_dir = dataset_dir(dataset_id) / "chunks"
    total = count_records(chunks_dir / "chunks.jsonl")
    kept = count_records(chunks_dir / "chunks_filtered.jsonl")
    rejected = count_records(chunks_dir / "chunks_rejected.jsonl")
    processed = min(kept + rejected, total)

    return {
        "processed": processed,
        "total": total,
        "kept": kept,
        "rejected": rejected,
        "remaining": max(total - processed, 0),
        "progress": (processed / total) if total else 0,
    }


def reset_filter_outputs(dataset_id: str) -> None:
    chunks_dir = dataset_dir(dataset_id) / "chunks"
    for filename in ("chunks_filtered.jsonl", "chunks_rejected.jsonl"):
        (chunks_dir / filename).unlink(missing_ok=True)


def default_filter_config() -> FilterConfig:
    return {
        "lexicon": load_xlsx(KNOWLEDGE_BASE_PATH, "lexicon", "lexicon"),
        "query": load_xlsx(KNOWLEDGE_BASE_PATH, "query", "query"),
        "threshold": CHUNK_FILTER_THRESHOLD,
    }


def _config_path(dataset_id: str) -> Path:
    return dataset_dir(dataset_id) / FILTER_CONFIG_FILENAME


def load_filter_config(dataset_id: str) -> FilterConfig:
    path = _config_path(dataset_id)
    if not path.exists():
        config = default_filter_config()
        save_filter_config(dataset_id, config)
        return config

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        "lexicon": [str(value) for value in data.get("lexicon", [])],
        "query": [str(value) for value in data.get("query", [])],
        "threshold": float(data.get("threshold", CHUNK_FILTER_THRESHOLD)),
    }


def save_filter_config(dataset_id: str, config: FilterConfig) -> None:
    path = _config_path(dataset_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
