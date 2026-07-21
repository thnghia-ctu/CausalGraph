from dataclasses import dataclass
from src.data_models.trigger import Trigger
from src.data_models.factor import Factor
from src.data_models.dependency_token import Sentence

@dataclass
class Relation:
    source: Factor | None
    trigger: Trigger
    relationship: str
    target: Factor | None
    confidence: float = 1.0
    doc_id: str | None = None
    sentence: Sentence | None = None
