from dataclasses import dataclass

from src.data_models.factor import Factor


@dataclass
class ConceptState:
    concept_candidate: Factor | None
    state: str | None
