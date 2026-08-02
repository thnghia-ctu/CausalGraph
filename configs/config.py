from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

CAUSAL_TRIGGERS_PATH = BASE_DIR / "configs/causal_triggers.xlsx"
KNOWLEDGE_BASE_PATH = BASE_DIR / "configs/knowledge/knowledge_base.xlsx"
UNIQUE_LINKS_PATH = BASE_DIR / "data/links/unique_links.csv"
MANIFEST_PATH = BASE_DIR / "data/raw/manifest.jsonl"

CHUNKS_DIR = BASE_DIR / "data/chunks"
FILTERED_CHUNKS_PATH = CHUNKS_DIR / "chunks_filtered.jsonl"
REJECTED_CHUNKS_PATH = CHUNKS_DIR / "chunks_rejected.jsonl"

CHUNK_FILTER_THRESHOLD = 0.38

CAUSAL_SENTENCES_DIR = BASE_DIR / "data/causal_sentences"
CAUSAL_SENTENCES_PATH = CAUSAL_SENTENCES_DIR / "causal_sentences.csv"

LLM_RELATIONS_DIR = BASE_DIR / "data/llm_relations"
LLM_RELATIONS_PATH = LLM_RELATIONS_DIR / "relations.csv"
RELATIONS_REJECTED_PATH = LLM_RELATIONS_DIR / "relations_rejected.csv"

GRAPH_DIR = BASE_DIR / "data/graph"
RELATIONS_WITH_CONCEPT_PATH = GRAPH_DIR / "relations_with_concept.csv"
CONCEPTS_PATH = GRAPH_DIR / "concepts.jsonl"

CONCEPT_CLUSTER_DISTANCE_THRESHOLD = 0.25