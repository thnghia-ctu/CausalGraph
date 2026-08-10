import json
from pathlib import Path

from configs.config import CACHE_DIR, CHUNK_FILTER_THRESHOLD, KNOWLEDGE_BASE_PATH
from src.utils.helpers import load_xlsx

KNOWLEDGE_BASE_FILENAME = "knowledge_base.json"


def _default_knowledge_base() -> dict:
    return {
        "lexicon": load_xlsx(KNOWLEDGE_BASE_PATH, "lexicon", "lexicon"),
        "query": load_xlsx(KNOWLEDGE_BASE_PATH, "query", "query"),
        "threshold": CHUNK_FILTER_THRESHOLD,
    }


def load_knowledge_base(output_path: str | Path = CACHE_DIR) -> dict:
    path = Path(output_path) / KNOWLEDGE_BASE_FILENAME
    if not path.exists():
        data = _default_knowledge_base()
        save_knowledge_base(output_path, data)
        return data

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_knowledge_base(output_path: str | Path, data: dict) -> None:
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    path = output_path / KNOWLEDGE_BASE_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
