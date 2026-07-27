from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

CAUSAL_TRIGGERS_PATH = BASE_DIR / "configs/causal_triggers.xlsx"
KNOWLEDGE_BASE_PATH = BASE_DIR / "configs/knowledge/knowledge_base.xlsx"
UNIQUE_LINKS_PATH = BASE_DIR / "data/links/unique_links.csv"
MANIFEST_PATH = BASE_DIR / "data/raw/manifest.jsonl"