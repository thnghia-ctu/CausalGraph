"""Domain model for a normalized causal-factor mention."""

from dataclasses import dataclass
from typing import Literal

from src.data_models.state import State


MappingMethod = Literal[
    "preferred_label",
    "alias",
    "embedding",
    "unmapped",
]


@dataclass
class NormalizedFactor:
    """A factor mention mapped to a neutral concept and an optional state."""

    original_text: str
    normalized_text: str

    concept_candidate: str
    concept_id: str | None
    concept_label: str | None

    state: State | None

    confidence: float
    mapping_method: MappingMethod
    needs_review: bool = False

    @property
    def factor_core(self) -> str:
        """Backward-compatible name for ``concept_candidate``."""

        return self.concept_candidate

    @property
    def concept(self) -> str | None:
        """Backward-compatible name for ``concept_label``."""

        return self.concept_label
