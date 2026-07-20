"""Domain model for a normalized causal-factor state."""

from dataclasses import dataclass
from typing import Literal


StateCategory = Literal["CHANGE", "CONDITION"]

StateValue = Literal[
    "INCREASE",
    "DECREASE",
    "IMPROVE",
    "DETERIORATE",
    "HIGH",
    "LOW",
    "LACK",
    "SUFFICIENT",
    "LIMITED",
    "DIFFICULT",
    "AVAILABLE",
    "UNAVAILABLE",
]


STATE_CATEGORY_BY_VALUE: dict[StateValue, StateCategory] = {
    "INCREASE": "CHANGE",
    "DECREASE": "CHANGE",
    "IMPROVE": "CHANGE",
    "DETERIORATE": "CHANGE",
    "HIGH": "CONDITION",
    "LOW": "CONDITION",
    "LACK": "CONDITION",
    "SUFFICIENT": "CONDITION",
    "LIMITED": "CONDITION",
    "DIFFICULT": "CONDITION",
    "AVAILABLE": "CONDITION",
    "UNAVAILABLE": "CONDITION",
}


@dataclass(frozen=True)
class State:
    category: StateCategory
    value: StateValue
    expression: str
    negated: bool = False
