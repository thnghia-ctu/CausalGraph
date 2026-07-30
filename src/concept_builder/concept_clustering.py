from collections import Counter
from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

from src.utils.embedding import encode_texts
from src.utils.text_normalization import normalize_surface

CLUSTER_COLUMNS = ("concept_candidate", "count", "cluster")
CONCEPT_COLUMNS = ("concept_id", "representative_label", "members")


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
