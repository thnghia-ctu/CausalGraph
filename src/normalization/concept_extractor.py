"""Rule-first extraction of a neutral concept candidate."""

from __future__ import annotations

import re
from collections.abc import Callable

from src.normalization.state_normalizer import StateMatch


ExtractionFallback = Callable[[str, StateMatch | None], str | None]


class ConceptExtractor:
    """Extract concept core with surface rules and optional NLP fallbacks.

    POS/dependency implementations can be injected through ``fallbacks``.
    They are consulted only when deterministic surface extraction produces no
    candidate, keeping parser-dependent behavior out of the domain pipeline.
    """

    _LEADING_FILLER_PATTERN = re.compile(
        r"^(?:(?:trong|về) việc|đối với|về)\s+"
    )
    _TRAILING_FILLER_PATTERN = re.compile(
        r"\s+(?:(?:vẫn\s+)?còn|đang|bị|được|trở nên|ngày càng)$"
    )
    _POST_STATE_CONTEXT_PATTERN = re.compile(
        r"^(?:[,.;:]|(?:nhưng|nên|mà|do|vì|khi|nhờ|tại|ở|trong|"
        r"so với|hơn)\b)"
    )
    _POSTPOSITIVE_STATES = frozenset({"HIGH", "LOW", "LIMITED"})

    def __init__(
        self,
        fallbacks: tuple[ExtractionFallback, ...] = (),
    ) -> None:
        self.fallbacks = fallbacks

    def extract(
        self,
        text: str,
        state_match: StateMatch | None,
    ) -> str:
        """Extract a concept candidate from surface-normalized text."""

        if state_match is None:
            candidate = self._clean_core(text)
        else:
            before = text[:state_match.span_start].strip()
            after = text[state_match.span_end:].strip()

            if not before:
                candidate = self._clean_core(after)
            elif not after:
                candidate = self._clean_core(before)
            elif (
                state_match.value in self._POSTPOSITIVE_STATES
                or self._POST_STATE_CONTEXT_PATTERN.match(after)
            ):
                candidate = self._clean_core(before)
            else:
                candidate = self._clean_core(after)

        if candidate:
            return candidate

        for fallback in self.fallbacks:
            candidate = self._clean_core(fallback(text, state_match) or "")
            if candidate:
                return candidate

        # Conservative OOV fallback: retain the normalized mention instead of
        # inventing a concept or forcing a vocabulary match.
        return self._clean_core(text)

    @classmethod
    def _clean_core(cls, text: str) -> str:
        core = text.strip(" \t\n\r,.;:!?–—-()[]{}\"'“”‘’")
        core = cls._LEADING_FILLER_PATTERN.sub("", core)
        core = cls._TRAILING_FILLER_PATTERN.sub("", core)
        return re.sub(r"\s+", " ", core).strip()
