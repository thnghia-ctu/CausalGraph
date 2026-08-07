from collections import Counter
from collections.abc import Sequence

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

from src.utils.embedding import encode_texts
from src.utils.text_normalization import normalize_surface

CLUSTER_COLUMNS = ("concept_candidate", "count", "cluster")
CONCEPT_COLUMNS = ("concept_id", "representative_label", "members")

MIN_SENTENCE_COUNT = 2
MAX_SAMPLE_RELATIONS = 20
RELATION_DETAIL_COLUMNS = [
    "subject_text", "predicate", "object_text", "original_sentence", "simple_sentence", "url",
    "source_direction", "target_direction",
]


def cluster_concepts(
    candidates: Sequence[str],
    *,
    distance_threshold: float,
    model: object | None = None,
) -> pd.DataFrame:
    counts = Counter(
        normalized
        for candidate in candidates
        if (normalized := normalize_surface(str(candidate)))
    )
    unique_candidates = list(counts)
    if not unique_candidates:
        return pd.DataFrame(columns=CLUSTER_COLUMNS)

    if len(unique_candidates) == 1:
        labels = np.zeros(1, dtype=int)
    else:
        embeddings = encode_texts(unique_candidates, model, normalize_embeddings=True)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(embeddings)

    return pd.DataFrame({
        "concept_candidate": unique_candidates,
        "count": [counts[candidate] for candidate in unique_candidates],
        "cluster": labels,
    })


def build_concept_table(clustered: pd.DataFrame) -> pd.DataFrame:
    if clustered.empty:
        return pd.DataFrame(columns=CONCEPT_COLUMNS)

    cluster_order = (
        clustered.groupby("cluster")["count"].sum().sort_values(ascending=False).index
    )
    records = []
    for rank, cluster in enumerate(cluster_order, start=1):
        members = clustered[clustered["cluster"] == cluster].sort_values(
            ["count", "concept_candidate"], ascending=[False, True]
        )
        records.append({
            "concept_id": f"C{rank:04d}",
            "representative_label": members.iloc[0]["concept_candidate"],
            "members": members["concept_candidate"].tolist(),
        })
    return pd.DataFrame(records, columns=CONCEPT_COLUMNS)


def assign_concept_ids(
    relations: pd.DataFrame,
    concepts: pd.DataFrame,
) -> pd.DataFrame:
    candidate_to_id = {
        member: row.concept_id
        for row in concepts.itertuples()
        for member in row.members
    }

    def lookup(value):
        if pd.isna(value):
            return None
        return candidate_to_id.get(normalize_surface(str(value)))

    result = relations.copy()
    result["source_concept_id"] = result["source_concept_candidate"].map(lookup)
    result["target_concept_id"] = result["target_concept_candidate"].map(lookup)
    return result


def build_concepts_from_relations(
    relations: pd.DataFrame,
    *,
    distance_threshold: float,
    model: object | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = pd.concat([
        relations["source_concept_candidate"],
        relations["target_concept_candidate"],
    ]).dropna()

    clustered = cluster_concepts(
        candidates,
        distance_threshold=distance_threshold,
        model=model,
    )
    concepts = build_concept_table(clustered)
    relations_with_ids = assign_concept_ids(relations, concepts)
    return relations_with_ids, concepts


def _direction_category(seen: set[int]) -> str:
    has_positive = 1 in seen
    has_negative = -1 in seen
    if has_positive and has_negative:
        return "conflict"
    if has_positive:
        return "positive"
    if has_negative:
        return "negative"
    return "neutral"


def build_graph_from_relations(
    relations_with_ids: pd.DataFrame,
    concepts: pd.DataFrame,
    *,
    min_sentence_count: int = MIN_SENTENCE_COUNT,
    max_sample_relations: int = MAX_SAMPLE_RELATIONS,
) -> nx.DiGraph:
    labels = dict(zip(concepts["concept_id"], concepts["representative_label"]))

    relations = relations_with_ids.dropna(subset=["source_concept_id", "target_concept_id"])
    grouped = relations.groupby(["source_concept_id", "target_concept_id"])
    edge_stats = grouped.agg(
        relation_count=("simple_sentence", "size"),
        sentence_count=("simple_sentence", "nunique"),
    ).reset_index()
    edges = edge_stats[edge_stats["sentence_count"] >= min_sentence_count]

    graph = nx.DiGraph()
    directions: dict[str, set[int]] = {}
    for source_id, target_id, relation_count, sentence_count in edges.itertuples(index=False):
        rows = grouped.get_group((source_id, target_id)).head(max_sample_relations)
        details = rows[RELATION_DETAIL_COLUMNS].to_dict("records")
        graph.add_edge(
            labels.get(source_id, source_id),
            labels.get(target_id, target_id),
            relation=f"{sentence_count} câu nguồn độc lập ({relation_count} quan hệ)",
            score=sentence_count,
            relations=details,
        )
        for detail in details:
            directions.setdefault(source_id, set()).add(detail["source_direction"])
            directions.setdefault(target_id, set()).add(detail["target_direction"])

    node_categories = {
        labels.get(concept_id, concept_id): _direction_category(seen)
        for concept_id, seen in directions.items()
        if labels.get(concept_id, concept_id) in graph.nodes
    }
    nx.set_node_attributes(graph, node_categories, "direction_state")
    return graph
