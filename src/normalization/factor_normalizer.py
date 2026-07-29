"""Normalize causal-factor text into concept and state records."""

from dataclasses import replace
from pathlib import Path
import re

from src.data_models.dependency_token import DependencyToken, Sentence
from src.data_models.factor import Factor
from src.data_models.normalized_factor import NormalizedFactor
from src.normalization.concept_extractor import ConceptExtractor
from src.normalization.concept_mapper import (
    ConceptMapper,
    EmbeddingConceptMatcher,
    MappingPolicy,
)
from src.normalization.concept_vocabulary import ConceptVocabulary
from src.normalization.state_normalizer import StateMatch, StateNormalizer
from src.utils.text_normalization import normalize_surface, remove_noise_tokens


class FactorNormalizer:
    """Run surface, state, concept, and vocabulary normalization."""

    _SEPARATOR = re.compile(
        r"\s*(?P<value>[,;]|\bvà\b|\bhoặc\b|\bnhưng\b)\s*"
    )
    _STRONG_SEPARATORS = {";", "nhưng"}

    def __init__(
        self,
        state_normalizer: StateNormalizer | None = None,
        concept_extractor: ConceptExtractor | None = None,
        concept_mapper: ConceptMapper | None = None,
    ) -> None:
        self.state_normalizer = state_normalizer or StateNormalizer()
        self.concept_extractor = concept_extractor or ConceptExtractor()
        self.concept_mapper = concept_mapper or ConceptMapper()

    @classmethod
    def from_vocabulary_xlsx(
        cls,
        concept_vocabulary_path: str | Path,
        *,
        state_lexicon_path: str | Path | None = None,
        use_embeddings: bool = True,
        embedding_model: object | None = None,
        auto_accept_threshold: float = 0.85,
        review_threshold: float = 0.65,
        top_k: int = 5,
    ) -> "FactorNormalizer":
        vocabulary = ConceptVocabulary.from_xlsx(concept_vocabulary_path)
        matcher = (
            EmbeddingConceptMatcher(vocabulary, model=embedding_model)
            if use_embeddings
            else None
        )
        mapper = ConceptMapper(
            vocabulary,
            matcher,
            MappingPolicy(auto_accept_threshold, review_threshold),
            top_k,
        )
        return cls(StateNormalizer(state_lexicon_path), concept_mapper=mapper)

    def normalize(self, text: str) -> NormalizedFactor:
        """Normalize one factor without decomposing it."""

        normalized = self._normalize_text(text)
        match = self.state_normalizer.normalize(normalized)
        return self._build(text, normalized, match)

    def normalize_many(self, text: str) -> list[NormalizedFactor]:
        """Split only independent state clauses; otherwise keep one factor."""

        return self._normalize_many(text, None)

    def normalize_factor(
        self,
        factor: Factor,
        sentence: Sentence,
    ) -> list[NormalizedFactor]:
        """Normalize a parsed factor and split coordinated shared concepts."""

        factor_ids = set(factor.token_ids)
        tokens = [token for token in sentence.tokens if token.id in factor_ids]
        return self._normalize_many(factor.text, tokens)

    def _normalize_many(
        self,
        original: str,
        tokens: list[DependencyToken] | None,
    ) -> list[NormalizedFactor]:
        normalized = self._normalize_text(original)
        matches = self.state_normalizer.find_all(normalized)
        segments = self._state_segments(normalized, matches)

        if len(segments) == 1:
            match = matches[0] if matches else None
            result = self._build(original, normalized, match)
            return self._split_coordination(result, match, tokens)

        results: list[NormalizedFactor] = []
        for segment in segments:
            match = self.state_normalizer.normalize(segment)
            result = self._build(original, segment, match)
            segment_tokens = self._tokens_in(segment, tokens)
            results.extend(self._split_coordination(result, match, segment_tokens))
        return results

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("Factor text must be a string")
        return remove_noise_tokens(normalize_surface(text))

    def _state_segments(
        self,
        text: str,
        matches: list[StateMatch],
    ) -> list[str]:
        if len(matches) < 2:
            return [text]

        cuts: list[tuple[int, int]] = []
        for left, right in zip(matches, matches[1:]):
            separators = list(self._SEPARATOR.finditer(text, left.end, right.start))
            if not separators:
                return [text]
            strong = [
                item
                for item in separators
                if item.group("value") in self._STRONG_SEPARATORS
            ]
            boundary = (strong or separators)[-1]
            cuts.append(boundary.span())

        segments: list[str] = []
        start = 0
        for end, next_start in cuts:
            segments.append(text[start:end].strip())
            start = next_start
        segments.append(text[start:].strip())
        return segments if all(segments) else [text]

    def _split_coordination(
        self,
        result: NormalizedFactor,
        match: StateMatch | None,
        tokens: list[DependencyToken] | None,
    ) -> list[NormalizedFactor]:
        if match is None or match.span_start != 0 or not tokens:
            return [result]

        token_map = {token.id: token for token in tokens}
        for coord in tokens:
            if coord.word.casefold() != "và" or coord.dep != "coord":
                continue
            head = token_map.get(coord.head)
            conjs = [
                token for token in tokens
                if token.head == coord.id and token.dep == "conj"
            ]
            if not self._compatible(head, conjs, match):
                continue

            state_text = result.normalized_text[match.span_start:match.span_end]
            state_ids = {
                token.id
                for token in tokens
                if normalize_surface(token.word) in state_text
            }
            left = self._subtree(head, token_map, exclude=coord.id) - state_ids
            right = self._subtree(conjs[0], token_map) - state_ids
            shared = {
                token.id for token in tokens
                if token.id < head.id
                and token.pos != "CH"
                and token.id not in state_ids
            }
            candidates = [
                self._surface(shared | branch, token_map)
                for branch in (left, right)
            ]
            if all(candidates):
                return [
                    self._replace_candidate(result, state_text, candidate)
                    for candidate in candidates
                ]
        return [result]

    @staticmethod
    def _compatible(
        head: DependencyToken | None,
        conjs: list[DependencyToken],
        match: StateMatch,
    ) -> bool:
        if head is None or len(conjs) != 1:
            return False
        head_pos = "N" if head.pos.startswith("N") else head.pos
        conj_pos = "N" if conjs[0].pos.startswith("N") else conjs[0].pos
        return (
            head_pos == conj_pos
            and normalize_surface(head.word) not in match.expression
        )

    @staticmethod
    def _tokens_in(
        text: str,
        tokens: list[DependencyToken] | None,
    ) -> list[DependencyToken] | None:
        if not tokens:
            return None
        words = set(text.split())
        selected = [
            token for token in tokens
            if set(normalize_surface(token.word).split()) <= words
        ]
        return selected or None

    @classmethod
    def _subtree(
        cls,
        root: DependencyToken,
        token_map: dict[int, DependencyToken],
        exclude: int | None = None,
    ) -> set[int]:
        ids = {root.id}
        for child in token_map.values():
            if child.head == root.id and child.id != exclude:
                ids.update(cls._subtree(child, token_map))
        return ids

    @staticmethod
    def _surface(
        ids: set[int],
        token_map: dict[int, DependencyToken],
    ) -> str:
        return " ".join(
            normalize_surface(token_map[token_id].word)
            for token_id in sorted(ids)
            if token_map[token_id].pos != "CH"
        )

    def _replace_candidate(
        self,
        result: NormalizedFactor,
        state_text: str,
        candidate: str,
    ) -> NormalizedFactor:
        candidate = self.concept_extractor.extract(candidate, None)
        mapping = self.concept_mapper.map(candidate)
        return replace(
            result,
            normalized_text=f"{state_text} {candidate}".strip(),
            concept_candidate=candidate,
            concept_id=mapping.concept_id,
            concept_label=mapping.concept_label,
            confidence=mapping.confidence,
            mapping_method=mapping.method,
            needs_review=mapping.needs_review,
        )

    def _build(
        self,
        original: str,
        normalized: str,
        match: StateMatch | None,
    ) -> NormalizedFactor:
        candidate = self.concept_extractor.extract(normalized, match)
        mapping = self.concept_mapper.map(candidate)
        return NormalizedFactor(
            original_text=original,
            normalized_text=normalized,
            concept_candidate=candidate,
            concept_id=mapping.concept_id,
            concept_label=mapping.concept_label,
            state=match.state if match else None,
            confidence=mapping.confidence,
            mapping_method=mapping.method,
            needs_review=mapping.needs_review,
        )
