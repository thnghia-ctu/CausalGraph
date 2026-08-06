from dataclasses import dataclass

@dataclass(frozen=True)
class ConceptFactor:
    factor_text: str
    concept_candidate: str = ""
    concept_id: str = ""
    state: str = ""
    state_value: str = ""
    negated: bool = False
