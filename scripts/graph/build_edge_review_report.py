import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import CONCEPTS_PATH, GRAPH_DIR, RELATIONS_WITH_CONCEPT_PATH
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT
from src.graph.edge_review_report import build_report

OUTPUT_PATH = GRAPH_DIR / "edge_review_report.xlsx"


def main():
    concepts = pd.read_json(CONCEPTS_PATH, lines=True)
    relations = pd.read_csv(RELATIONS_WITH_CONCEPT_PATH)

    output_path = build_report(
        relations, concepts, OUTPUT_PATH, min_sentence_count=MIN_SENTENCE_COUNT,
    )

    print(f"Xuất báo cáo đánh giá -> {output_path}")


if __name__ == "__main__":
    main()
