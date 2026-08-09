from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

CAUSAL_TRIGGERS_PATH = BASE_DIR / "configs/causal_triggers.xlsx"
KNOWLEDGE_BASE_PATH = BASE_DIR / "configs/knowledge/knowledge_base.xlsx"
UNIQUE_LINKS_PATH = BASE_DIR / "data/links/unique_links.csv"
DOCUMENTS_PATH = BASE_DIR / "data/raw/documents.jsonl"

CACHE_DIR = BASE_DIR / "cache"

CHUNKS_DIR = BASE_DIR / "data/chunks"
FILTERED_CHUNKS_PATH = CHUNKS_DIR / "chunks_filtered.jsonl"
REJECTED_CHUNKS_PATH = CHUNKS_DIR / "chunks_rejected.jsonl"

CHUNK_FILTER_THRESHOLD = 0.38

CAUSAL_SENTENCES_DIR = BASE_DIR / "data/causal_sentences"
CAUSAL_SENTENCES_PATH = CAUSAL_SENTENCES_DIR / "causal_sentences.csv"

DATASET_DIR = BASE_DIR / "data/dataset"
CAUSAL_SENTENCES_VERIFIED_PATH = DATASET_DIR / "causal_sentences.csv"

CAUSAL_CLASSIFIER_MODEL_PATH = BASE_DIR / "models/causal_classifier.joblib"
CAUSAL_CLASSIFIER_HF_REPO_ID = "thnghia-ctu/vi-causal-sentence-svm"
CAUSAL_FASTTEXT_MODEL_PATH = BASE_DIR / "models/causal_classifier_fasttext.bin"
CAUSAL_FASTTEXT_HF_REPO_ID = "thnghia-ctu/vi-causal-sentence-fasttext"

LLM_RELATIONS_DIR = BASE_DIR / "data/llm_relations"
LLM_RELATIONS_PATH = LLM_RELATIONS_DIR / "relations.csv"
RELATIONS_REJECTED_PATH = LLM_RELATIONS_DIR / "relations_rejected.csv"

SIMPLIFICATION_SENTENCES_PATH = BASE_DIR / "data/simplification/simplificated_sentences.csv"
SIMPLIFIER_MODEL_DIR = BASE_DIR / "models/simplifier"
SIMPLIFIER_HF_REPO_ID = "thnghia-ctu/vi-sentence-simplifier"

SPO_TAGGER_MODEL_DIR = BASE_DIR / "models/spo_tagger"
SPO_TAGGER_HF_REPO_ID = "thnghia-ctu/vi-spo-tagger"
SPO_RELATIONS_PATH = BASE_DIR / "data/SPO/relations.csv"
SPO_PREDICTIONS_PATH = BASE_DIR / "data/SPO/relations_predicted.csv"

CONCEPT_STATE_TAGGER_MODEL_DIR = BASE_DIR / "models/concept_state_tagger"
CONCEPT_STATE_TAGGER_HF_REPO_ID = "thnghia-ctu/vi-concept-state-tagger"
CONCEPT_STATE_RELATIONS_PATH = BASE_DIR / "data/concept_state/relations.csv"
CONCEPT_STATE_PREDICTIONS_PATH = BASE_DIR / "data/concept_state/relations_predicted.csv"

GRAPH_DIR = BASE_DIR / "data/graph"
RELATIONS_WITH_CONCEPT_PATH = GRAPH_DIR / "relations_with_concept.csv"
CONCEPTS_PATH = GRAPH_DIR / "concepts.jsonl"

CONCEPT_CLUSTER_DISTANCE_THRESHOLD = 0.25