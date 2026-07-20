"""Domain models used while mapping a concept candidate."""

from dataclasses import dataclass

from src.data_models.normalized_factor import MappingMethod


@dataclass(frozen=True)
class ControlledConcept:
    """A stable concept and its expert-approved surface aliases."""

    concept_id: str
    preferred_label: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticCandidate:
    """A controlled concept proposed by semantic similarity."""

    concept: ControlledConcept
    score: float


@dataclass(frozen=True)
class ConceptMapping:
    """Decision produced by concept matching and its acceptance policy."""

    concept_id: str | None
    concept_label: str | None
    confidence: float
    method: MappingMethod
    needs_review: bool
