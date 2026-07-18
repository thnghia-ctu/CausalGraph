import re

from src.data_models.normalized_factor import NormalizedFactor
from src.normalization.state_normalizer import StateMatch, StateNormalizer
from src.utils.text_normalization import normalize_surface, remove_noise_tokens


class FactorParser:
    """Phân tích factor mention thành factor core và state.

    Parser trả thẳng về ``NormalizedFactor`` thay vì tạo một ParsedFactor
    trung gian. Tại bước này, ``concept_id`` và ``concept`` có thể là
    ``None``; chúng sẽ được gán ở bước concept normalization sau đó.
    """

    _LEADING_FILLER_PATTERN = re.compile(
        r"^(?:(?:trong|về) việc|đối với|về)\s+"
    )
    _TRAILING_FILLER_PATTERN = re.compile(
        r"\s+(?:(?:vẫn\s+)?còn|đang|bị|được|trở nên|ngày càng)$"
    )
    _POST_STATE_CONTEXT_PATTERN = re.compile(
        r"^(?:[,.;:]|(?:nhưng|nên|mà|do|vì|khi|nhờ|tại|ở|trong|"
        r"so với|rõ rệt|đáng kể|mạnh(?: mẽ)?|nhanh(?: chóng)?|hơn)\b)"
    )
    _POSTPOSITIVE_STATES = {"HIGH", "LOW", "LIMITED"}

    def __init__(self, state_normalizer: StateNormalizer) -> None:
        self.state_normalizer = state_normalizer

    def parse(self, text: str) -> NormalizedFactor:
        """Phân tích source hoặc target thành factor core và state.

        Args:
            text: Nội dung source hoặc target của causal relation.

        Returns:
            ``NormalizedFactor`` chứa ``original_text``, ``factor_core`` và
            ``state``. Các trường concept chưa cần được gán tại bước này.
        """
        normalized_text = remove_noise_tokens(normalize_surface(text))
        state_match = self.state_normalizer.normalize(normalized_text)

        factor_core = normalized_text
        state = None
        if state_match is not None:
            factor_core = self._extract_factor_core(
                normalized_text,
                state_match,
            )
            state = state_match.state

        return NormalizedFactor(
            original_text=text,
            factor_core=factor_core,
            concept_id=None,
            concept=None,
            state=state,
        )

    def _extract_factor_core(
        self,
        text: str,
        state_match: StateMatch,
    ) -> str:
        before = text[:state_match.start].strip()
        after = text[state_match.end:].strip()

        if not before:
            core = after
        elif not after:
            core = before
        elif (
            state_match.state in self._POSTPOSITIVE_STATES
            or self._POST_STATE_CONTEXT_PATTERN.match(after)
        ):
            core = before
        else:
            core = after

        return self._clean_core(core)

    @classmethod
    def _clean_core(cls, text: str) -> str:
        core = text.strip(" \t\n\r,.;:!?–—-()[]{}\"'“”‘’")
        core = cls._LEADING_FILLER_PATTERN.sub("", core)
        core = cls._TRAILING_FILLER_PATTERN.sub("", core)
        return re.sub(r"\s+", " ", core).strip()
