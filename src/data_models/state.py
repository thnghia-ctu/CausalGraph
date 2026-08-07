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

STATE_DIRECTION_BY_VALUE: dict[StateValue, int] = {
    "INCREASE": 1,
    "DECREASE": -1,
    "IMPROVE": 1,
    "DETERIORATE": -1,
    "HIGH": 1,
    "LOW": -1,
    "LACK": -1,
    "SUFFICIENT": 1,
    "LIMITED": -1,
    "DIFFICULT": -1,
    "AVAILABLE": 1,
    "UNAVAILABLE": -1,
}


@dataclass(frozen=True)
class State:
    category: StateCategory
    value: StateValue
    expression: str
    negated: bool = False

    @property
    def direction(self) -> int:
        if self.negated:
            return 0
        return STATE_DIRECTION_BY_VALUE.get(self.value, 0)
