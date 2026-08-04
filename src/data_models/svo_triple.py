from dataclasses import dataclass

from src.data_models.factor import Factor


@dataclass
class SVOTriple:
    subject: Factor | None
    predicate: str
    object: Factor | None
