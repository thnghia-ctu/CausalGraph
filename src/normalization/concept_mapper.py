"""Exact and semantic mapping of concept candidates."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from src.data_models.concept import (
    ConceptMapping,
    ControlledConcept,
    SemanticCandidate,
)
from src.normalization.concept_vocabulary import ConceptVocabulary
from src.utils.embedding import encode_texts
from src.utils.text_normalization import normalize_surface


class SemanticMatcher(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[SemanticCandidate]: ...


class EmbeddingConceptMatcher:
    """Generate semantic candidates; it never makes acceptance decisions."""

    def __init__(
        self,
        vocabulary: ConceptVocabulary,
        model: object | None = None,
    ) -> None:
        self.vocabulary = vocabulary
        self._model = model
        self._entries: tuple[tuple[str, ControlledConcept], ...] = tuple(
            (normalize_surface(label), concept)
            for concept in vocabulary.concepts
            for label in (concept.preferred_label, *concept.aliases)
        )
        self._embeddings: np.ndarray | None = None

    def _encode(self, texts: list[str]) -> np.ndarray:
        return encode_texts(texts, model=self._model, normalize_embeddings=True)

    def search(self, query: str, top_k: int = 5) -> list[SemanticCandidate]:
        if top_k <= 0 or not self._entries:
            return []
        if self._embeddings is None:
            self._embeddings = self._encode(
                [label for label, _ in self._entries]
            )

        query_embedding = self._encode([normalize_surface(query)])[0]
        scores = self._embeddings @ query_embedding
        best_by_concept: dict[str, SemanticCandidate] = {}
        for (_, concept), raw_score in zip(self._entries, scores, strict=True):
            score = float(raw_score)
            existing = best_by_concept.get(concept.concept_id)
            if existing is None or score > existing.score:
                best_by_concept[concept.concept_id] = SemanticCandidate(
                    concept=concept,
                    score=score,
                )
        return sorted(
            best_by_concept.values(),
            key=lambda candidate: candidate.score,
            reverse=True,
        )[:top_k]


class MappingPolicy:
    """Separate semantic candidate generation from acceptance decisions."""

    def __init__(
        self,
        auto_accept_threshold: float = 0.85,
        review_threshold: float = 0.65,
    ) -> None:
        if not 0.0 <= review_threshold <= auto_accept_threshold <= 1.0:
            raise ValueError(
                "Thresholds must satisfy 0 <= review <= auto_accept <= 1"
            )
        self.auto_accept_threshold = auto_accept_threshold
        self.review_threshold = review_threshold

    def decide(
        self,
        candidates: list[SemanticCandidate],
    ) -> ConceptMapping:
        if not candidates:
            return self.unmapped()

        best = max(candidates, key=lambda candidate: candidate.score)
        confidence = min(1.0, max(0.0, best.score))
        if confidence >= self.review_threshold:
            return ConceptMapping(
                concept_id=best.concept.concept_id,
                concept_label=best.concept.preferred_label,
                confidence=confidence,
                method="embedding",
                needs_review=confidence < self.auto_accept_threshold,
            )
        return self.unmapped(confidence=confidence)

    @staticmethod
    def unmapped(confidence: float = 0.0) -> ConceptMapping:
        return ConceptMapping(
            concept_id=None,
            concept_label=None,
            confidence=confidence,
            method="unmapped",
            needs_review=True,
        )


class ConceptMapper:
    """Apply exact lookup, semantic search, then mapping policy."""

    def __init__(
        self,
        vocabulary: ConceptVocabulary | None = None,
        semantic_matcher: SemanticMatcher | None = None,
        policy: MappingPolicy | None = None,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        self.vocabulary = vocabulary or ConceptVocabulary()
        self.semantic_matcher = semantic_matcher
        self.policy = policy or MappingPolicy()
        self.top_k = top_k

    def map(self, candidate: str) -> ConceptMapping:
        exact = self.vocabulary.exact_match(candidate)
        if exact is not None:
            concept, method = exact
            return ConceptMapping(
                concept_id=concept.concept_id,
                concept_label=concept.preferred_label,
                confidence=1.0,
                method=method,
                needs_review=False,
            )
        if self.semantic_matcher is None:
            return self.policy.unmapped()
        return self.policy.decide(
            self.semantic_matcher.search(candidate, top_k=self.top_k)
        )
