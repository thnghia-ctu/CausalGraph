from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.utils.embedding import encode_texts
from src.utils.text_normalization import normalize_surface


CANDIDATE_MODEL_NAME = "keepitreal/vietnamese-sbert"
NEIGHBOR_COLUMNS = ("seed_candidate", "neighbor", "similarity", "rank")
REVIEW_COLUMNS = (
    "seed_candidate",
    "seed_count",
    "neighbor",
    "neighbor_count",
    "similarity",
    "rank",
    "decision",
    "concept_id",
    "reviewer_note",
)


def _normalize(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(
        value
        for text in values
        if (value := normalize_surface(text))
    ))


class CandidateNeighborFinder:
    def __init__(
        self,
        reference_candidates: Sequence[str],
        *,
        model: object | None = None,
        model_name: str = CANDIDATE_MODEL_NAME,
    ) -> None:
        self.references = _normalize(reference_candidates)
        self.model = model
        self.model_name = model_name
        self.embeddings = self._encode(self.references) if self.references else None

    def _encode(self, texts: Sequence[str]) -> np.ndarray:
        return encode_texts(
            texts,
            self.model,
            model_name=self.model_name,
            normalize_embeddings=True,
        )

    def find_top_k(
        self,
        seed_candidates: Sequence[str],
        *,
        top_k: int = 5,
    ) -> pd.DataFrame:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        seeds = _normalize(seed_candidates)
        if not seeds or self.embeddings is None:
            return pd.DataFrame(columns=NEIGHBOR_COLUMNS)

        scores = self._encode(seeds) @ self.embeddings.T
        rows = []
        for row, seed in enumerate(seeds):
            order = sorted(
                range(len(self.references)),
                key=lambda col: (-float(scores[row, col]), self.references[col]),
            )
            neighbors = [col for col in order if self.references[col] != seed][:top_k]
            rows.extend(
                {
                    "seed_candidate": seed,
                    "neighbor": self.references[col],
                    "similarity": float(scores[row, col]),
                    "rank": rank,
                }
                for rank, col in enumerate(neighbors, start=1)
            )
        return pd.DataFrame(rows, columns=NEIGHBOR_COLUMNS)


def build_candidate_review_queue(
    candidate_counts: pd.DataFrame,
    *,
    seed_limit: int = 100,
    top_k: int = 5,
    model: object | None = None,
    model_name: str = CANDIDATE_MODEL_NAME,
) -> pd.DataFrame:
    required = {"concept_candidate", "count"}
    missing = required - set(candidate_counts.columns)
    if missing:
        raise ValueError(f"Candidate counts are missing columns: {sorted(missing)}")
    if seed_limit <= 0:
        raise ValueError("seed_limit must be greater than zero")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    candidates = candidate_counts.copy()
    if "status" in candidates:
        status = candidates["status"].astype(str).str.strip().str.upper()
        candidates = candidates[status == "VALID"]

    candidates = candidates.dropna(subset=["concept_candidate", "count"])
    candidates["concept_candidate"] = candidates["concept_candidate"].map(
        lambda value: normalize_surface(str(value))
    )
    candidates["count"] = pd.to_numeric(candidates["count"], errors="raise")
    candidates = candidates[candidates["concept_candidate"] != ""]
    candidates = (
        candidates.groupby("concept_candidate", as_index=False)["count"]
        .sum()
        .sort_values(["count", "concept_candidate"], ascending=[False, True])
    )
    if candidates.empty:
        return pd.DataFrame(columns=REVIEW_COLUMNS)

    counts = candidates.set_index("concept_candidate")["count"]
    finder = CandidateNeighborFinder(
        candidates["concept_candidate"].tolist(),
        model=model,
        model_name=model_name,
    )
    queue = finder.find_top_k(
        candidates.head(seed_limit)["concept_candidate"].tolist(),
        top_k=top_k,
    )
    queue.insert(1, "seed_count", queue["seed_candidate"].map(counts))
    queue.insert(3, "neighbor_count", queue["neighbor"].map(counts))
    queue[["decision", "concept_id", "reviewer_note"]] = ""
    return queue[list(REVIEW_COLUMNS)]
