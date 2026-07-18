
from dataclasses import dataclass

@dataclass
class NormalizedFactor:
    original_text: str
    factor_core: str
    concept_id: str | None
    concept: str | None
    state: str | None