"""Detect normalized states from a small Excel lexicon."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import get_args

import pandas as pd

from configs.config import BASE_DIR
from src.data_models.state import (
    STATE_CATEGORY_BY_VALUE,
    State,
    StateCategory,
    StateValue,
)
from src.utils.text_normalization import normalize_surface


@dataclass(frozen=True)
class StateRule:
    expression: str
    state_category: StateCategory
    state_value: StateValue
    pattern: str = "surface"
    allowed_pos: tuple[str, ...] = ()


@dataclass(frozen=True)
class StateMatch:
    """A state expression and its negation-aware character span."""

    state: State
    start: int
    end: int
    span_start: int
    span_end: int

    @property
    def expression(self) -> str:
        return self.state.expression

    @property
    def value(self) -> StateValue:
        return self.state.value


class StateNormalizer:
    DEFAULT_PATH = BASE_DIR / "configs" / "state_lexicon.xlsx"
    DEFAULT_SHEET = "state_expressions"
    REQUIRED_COLUMNS = {"state_code", "expression"}

    _NEGATION = re.compile(
        r"(?:^|\s)(?P<value>không|chưa)(?:\s+(?:hề|thể))?\s*$"
    )

    def __init__(
        self,
        lexicon_path: str | Path | None = None,
        sheet_name: str = DEFAULT_SHEET,
    ) -> None:
        self.lexicon_path = Path(lexicon_path or self.DEFAULT_PATH)
        self.sheet_name = sheet_name
        self.rules = self._load_rules(self.lexicon_path, sheet_name)
        grouped: dict[StateValue, list[str]] = {}
        for rule in self.rules:
            grouped.setdefault(rule.state_value, []).append(rule.expression)
        self.state_lexicon = {
            value: tuple(expressions) for value, expressions in grouped.items()
        }
        self._patterns = tuple(
            (rule, re.compile(rf"(?<!\w){re.escape(rule.expression)}(?!\w)"))
            for rule in self.rules
        )

    @classmethod
    def _load_rules(
        cls,
        path: Path,
        sheet_name: str,
    ) -> tuple[StateRule, ...]:
        if not path.is_file():
            raise FileNotFoundError(f"State lexicon not found: {path}")

        frame = pd.read_excel(path, sheet_name=sheet_name)
        missing = cls.REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"State lexicon is missing columns: {sorted(missing)}")

        valid_values = set(get_args(StateValue))
        valid_categories = set(get_args(StateCategory))
        rules: list[StateRule] = []
        seen: set[tuple[str, str]] = set()
        for index, row in frame.iterrows():
            if pd.isna(row["state_code"]) or pd.isna(row["expression"]):
                raise ValueError(f"Empty state rule at Excel row {index + 2}")

            value = str(row["state_code"]).strip().upper()
            expression = normalize_surface(str(row["expression"]))
            if value not in valid_values or not expression:
                raise ValueError(f"Invalid state rule at Excel row {index + 2}")

            raw_category = row.get("state_category")
            category = (
                STATE_CATEGORY_BY_VALUE[value]
                if pd.isna(raw_category)
                else str(raw_category).strip().upper()
            )
            if category not in valid_categories:
                raise ValueError(f"Invalid state category at Excel row {index + 2}")

            key = (value, expression)
            if key in seen:
                continue
            seen.add(key)
            raw_pos = row.get("allowed_pos")
            allowed_pos = () if pd.isna(raw_pos) else tuple(
                value.strip()
                for value in re.split(r"[,;|]", str(raw_pos))
                if value.strip()
            )
            raw_pattern = row.get("pattern")
            pattern = "surface" if pd.isna(raw_pattern) else str(raw_pattern).strip()
            rules.append(StateRule(
                expression=expression,
                state_category=category,
                state_value=value,
                pattern=pattern or "surface",
                allowed_pos=allowed_pos,
            ))

        if not rules:
            raise ValueError(f"State lexicon sheet {sheet_name!r} is empty")
        return tuple(rules)

    @classmethod
    def _match(cls, rule: StateRule, text: str, start: int, end: int) -> StateMatch:
        span_start, span_end = start, end
        negated = False
        negation = cls._NEGATION.search(text[:start])
        if negation and not rule.expression.startswith(("không ", "chưa ")):
            negated = True
            span_start = negation.start("value")

        return StateMatch(
            state=State(
                category=rule.state_category,
                value=rule.state_value,
                expression=text[start:end],
                negated=negated,
            ),
            start=start,
            end=end,
            span_start=span_start,
            span_end=span_end,
        )

    def find_all(self, text: str) -> list[StateMatch]:
        """Return longest non-overlapping states in surface order."""

        matches = [
            self._match(rule, text, found.start(), found.end())
            for rule, pattern in self._patterns
            for found in pattern.finditer(text)
        ]
        matches.sort(key=lambda item: (item.start, -(item.end - item.start)))

        selected: list[StateMatch] = []
        for match in matches:
            overlaps = any(
                match.start < item.end and item.start < match.end
                for item in selected
            )
            if not overlaps:
                selected.append(match)
        return selected

    def normalize(self, text: str) -> StateMatch | None:
        matches = self.find_all(text)
        return matches[0] if matches else None
