"""Controlled concept vocabulary and exact lookup."""

from collections.abc import Iterable
from pathlib import Path
import re

import pandas as pd

from src.data_models.concept import ControlledConcept
from src.data_models.normalized_factor import MappingMethod
from src.utils.text_normalization import normalize_surface


class ConceptVocabulary:
    REQUIRED_CONCEPT_COLUMNS = {"concept_id", "preferred_label"}
    REQUIRED_ALIAS_COLUMNS = {"concept_id", "alias"}

    def __init__(self, concepts: Iterable[ControlledConcept] = ()) -> None:
        self.concepts = tuple(concepts)
        self._by_id: dict[str, ControlledConcept] = {}
        self._preferred_index: dict[str, ControlledConcept] = {}
        self._alias_index: dict[str, ControlledConcept] = {}

        for concept in self.concepts:
            concept_id = concept.concept_id.strip()
            preferred = concept.preferred_label.strip()
            if not concept_id or not preferred:
                raise ValueError("concept_id and preferred_label must not be empty")
            if concept_id in self._by_id:
                raise ValueError(f"Duplicate concept_id: {concept_id!r}")
            self._by_id[concept_id] = concept
            self._add(self._preferred_index, preferred, concept)
            for alias in concept.aliases:
                if not alias.strip():
                    raise ValueError(f"Empty alias for concept {concept_id!r}")
                self._add(self._alias_index, alias, concept)

        for label in self._preferred_index.keys() & self._alias_index.keys():
            if self._preferred_index[label] != self._alias_index[label]:
                raise ValueError(f"Vocabulary label {label!r} maps to multiple concepts")

    def __bool__(self) -> bool:
        return bool(self.concepts)

    @staticmethod
    def _add(
        index: dict[str, ControlledConcept],
        label: str,
        concept: ControlledConcept,
    ) -> None:
        key = normalize_surface(label)
        existing = index.get(key)
        if existing and existing.concept_id != concept.concept_id:
            raise ValueError(f"Duplicate label {label!r} for multiple concepts")
        index[key] = concept

    def exact_match(
        self,
        candidate: str,
    ) -> tuple[ControlledConcept, MappingMethod] | None:
        key = normalize_surface(candidate)
        if concept := self._preferred_index.get(key):
            return concept, "preferred_label"
        if concept := self._alias_index.get(key):
            return concept, "alias"
        return None

    @classmethod
    def from_xlsx(
        cls,
        path: str | Path,
        concepts_sheet: str = "concepts",
        aliases_sheet: str = "aliases",
    ) -> "ConceptVocabulary":
        workbook = Path(path)
        if not workbook.is_file():
            raise FileNotFoundError(f"Concept vocabulary not found: {workbook}")

        with pd.ExcelFile(workbook) as excel:
            sheets = set(excel.sheet_names)
        if concepts_sheet not in sheets:
            raise ValueError(f"Missing concept sheet {concepts_sheet!r}")

        frame = pd.read_excel(workbook, sheet_name=concepts_sheet)
        cls._require_columns(frame, cls.REQUIRED_CONCEPT_COLUMNS, concepts_sheet)
        records: dict[str, tuple[str, list[str]]] = {}
        for index, row in frame.iterrows():
            concept_id = cls._required(row.get("concept_id"), "concept_id", index)
            label = cls._required(row.get("preferred_label"), "preferred_label", index)
            if concept_id in records:
                raise ValueError(f"Duplicate concept_id: {concept_id!r}")
            records[concept_id] = (label, cls._split_aliases(row.get("aliases")))

        if aliases_sheet in sheets:
            aliases = pd.read_excel(workbook, sheet_name=aliases_sheet)
            cls._require_columns(aliases, cls.REQUIRED_ALIAS_COLUMNS, aliases_sheet)
            for index, row in aliases.iterrows():
                concept_id = cls._required(row.get("concept_id"), "concept_id", index)
                alias = cls._required(row.get("alias"), "alias", index)
                if concept_id not in records:
                    raise ValueError(f"Alias references unknown concept_id {concept_id!r}")
                records[concept_id][1].append(alias)

        return cls(
            ControlledConcept(
                concept_id=concept_id,
                preferred_label=label,
                aliases=tuple(dict.fromkeys(aliases)),
            )
            for concept_id, (label, aliases) in records.items()
        )

    @staticmethod
    def _require_columns(frame: pd.DataFrame, required: set[str], sheet: str) -> None:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Sheet {sheet!r} is missing columns: {sorted(missing)}")

    @staticmethod
    def _required(value: object, name: str, index: int) -> str:
        if pd.isna(value):
            raise ValueError(f"Empty {name} at Excel row {index + 2}")
        return str(value).strip()

    @staticmethod
    def _split_aliases(value: object) -> list[str]:
        if value is None or pd.isna(value):
            return []
        return [item.strip() for item in re.split(r"[;|\n]", str(value)) if item.strip()]
