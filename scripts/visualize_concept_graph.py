import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import CONCEPTS_PATH, GRAPH_DIR, RELATIONS_WITH_CONCEPT_PATH
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT, build_graph_from_relations
from src.graph.graph_visualizer import visualize_graph

OUTPUT_PATH = GRAPH_DIR / "concept_graph.html"


def build_graph(min_sentence_count: int = MIN_SENTENCE_COUNT):
    concepts = pd.read_json(CONCEPTS_PATH, lines=True)
    relations = pd.read_csv(RELATIONS_WITH_CONCEPT_PATH)
    return build_graph_from_relations(relations, concepts, min_sentence_count=min_sentence_count)


def main():
    full_edges = pd.read_csv(RELATIONS_WITH_CONCEPT_PATH)
    full_edges = full_edges.dropna(subset=["source_concept_id", "target_concept_id"])
    total_edges = full_edges.groupby(["source_concept_id", "target_concept_id"]).ngroups

    graph = build_graph()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    visualize_graph(graph, str(OUTPUT_PATH))

    print(
        f"Hiển thị {graph.number_of_nodes()} node, {graph.number_of_edges()}/"
        f"{total_edges} cạnh (min_sentence_count={MIN_SENTENCE_COUNT}) -> {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
