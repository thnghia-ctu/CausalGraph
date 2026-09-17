from pathlib import Path

import networkx as nx
import pandas as pd

from src.extraction.concept_state_runner import load_concept_states
from src.graph.graph_runner import GraphRunner


def build_dataset_graph(
    dataset_dir: str | Path,
    distance_threshold: float,
    min_edge_count: int,
) -> tuple[nx.DiGraph, Path]:
    dataset_dir = Path(dataset_dir)
    records = load_concept_states(dataset_dir)
    graph = GraphRunner().build_graph(
        records,
        output_path=dataset_dir,
        distance_threshold=distance_threshold,
        min_sentence_count=min_edge_count,
    )
    return graph, dataset_dir / "graph" / "concept_graph.html"


def load_graph_summary(dataset_dir: str | Path) -> dict[str, int | bool]:
    graph_dir = Path(dataset_dir) / "graph"
    concepts_path = graph_dir / "concepts.jsonl"
    relations_path = graph_dir / "relations_with_concept.csv"
    graph_path = graph_dir / "concept_graph.html"

    return {
        "nodes": sum(1 for _ in concepts_path.open(encoding="utf-8")) if concepts_path.exists() else 0,
        "edges": len(pd.read_csv(relations_path)) if relations_path.exists() else 0,
        "visible_edges": len(pd.read_csv(relations_path)) if relations_path.exists() else 0,
        "available": graph_path.exists(),
    }
