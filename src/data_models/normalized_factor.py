
from dataclasses import dataclass

@dataclass
class NormalizedFactor:
    original_text: str
    concept: str
    state: str | None