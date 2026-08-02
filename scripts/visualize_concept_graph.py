import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
import pandas as pd

from configs.config import CONCEPTS_PATH, GRAPH_DIR, RELATIONS_WITH_CONCEPT_PATH
from src.graph.graph_visualizer import visualize_graph

MIN_SENTENCE_COUNT = 2
MAX_SAMPLE_RELATIONS = 20
OUTPUT_PATH = GRAPH_DIR / "concept_graph.html"

RELATION_DETAIL_COLUMNS = ["subject_text", "predicate", "object_text", "original_sentence", "url"]


def build_graph(min_sentence_count: int = MIN_SENTENCE_COUNT) -> nx.DiGraph:
    concepts = pd.read_json(CONCEPTS_PATH, lines=True)
    labels = dict(zip(concepts["concept_id"], concepts["representative_label"]))

    relations = pd.read_csv(RELATIONS_WITH_CONCEPT_PATH)
    relations = relations.dropna(subset=["source_concept_id", "target_concept_id"])
    grouped = relations.groupby(["source_concept_id", "target_concept_id"])
    edge_stats = grouped.agg(
        relation_count=("original_sentence", "size"),
        sentence_count=("original_sentence", "nunique"),
    ).reset_index()
    edges = edge_stats[edge_stats["sentence_count"] >= min_sentence_count]

    graph = nx.DiGraph()
    for source_id, target_id, relation_count, sentence_count in edges.itertuples(index=False):
        rows = grouped.get_group((source_id, target_id)).head(MAX_SAMPLE_RELATIONS)
        details = rows[RELATION_DETAIL_COLUMNS].to_dict("records")
        graph.add_edge(
            labels.get(source_id, source_id),
            labels.get(target_id, target_id),
            relation=f"{sentence_count} câu nguồn độc lập ({relation_count} quan hệ)",
            score=sentence_count,
            relations=details,
        )
    return graph


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
