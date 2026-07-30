import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import (
    CONCEPT_CLUSTER_DISTANCE_THRESHOLD,
    CONCEPTS_PATH,
    LLM_RELATIONS_PATH,
    RELATIONS_REJECTED_PATH,
    RELATIONS_WITH_CONCEPT_PATH,
)
from src.concept_builder.concept_clustering import build_concepts_from_relations
from src.filtering.relation_filter import filter_relations
import src.utils.helpers as hlp


def main():
    relations = pd.read_csv(LLM_RELATIONS_PATH)
    valid, rejected = filter_relations(relations)
    hlp.save_to_csv(RELATIONS_REJECTED_PATH, rejected)

    relations_with_ids, concepts = build_concepts_from_relations(
        valid,
        distance_threshold=CONCEPT_CLUSTER_DISTANCE_THRESHOLD,
    )

    hlp.save_to_csv(RELATIONS_WITH_CONCEPT_PATH, relations_with_ids)
    CONCEPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    concepts.to_json(CONCEPTS_PATH, orient="records", lines=True, force_ascii=False)

    print(f"Rejected {len(rejected)}/{len(relations)} relations -> {RELATIONS_REJECTED_PATH}")
    print(f"Formed {len(concepts)} concepts -> {CONCEPTS_PATH}")
    print(f"Wrote {len(relations_with_ids)} relations -> {RELATIONS_WITH_CONCEPT_PATH}")


if __name__ == "__main__":
    main()
