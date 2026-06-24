from dataclasses import dataclass
from src.data_models.trigger import Trigger

@dataclass
class Relation:
    source: str
    trigger: Trigger
    relationship: str
    target: str | None
    confidence: float = 1.0