"""List concept candidates and count their surface-normalized occurrences."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from configs.config import BASE_DIR
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.filtering.semantic_filter import filter_chunks
from src.utils.helpers import  load_txt

import pandas as pd

from src.utils.text_normalization import normalize_surface


DEFAULT_CANDIDATE_COLUMNS = (
    "concept_candidate",
    "source_concept_candidate",
    "target_concept_candidate",
)

def build_candidates_from_links(links:list[str]):

    for link in links:
        text = normalize_surface(load_txt(link))
    return ""


def load_candidates(
    input_path: str | Path,
    *,
    candidate_columns: Sequence[str] | None = None,
    sheet_name: str | int = 0,
) -> list[str]:

    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Candidate input file not found: {path}")

    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame = pd.read_csv(path, encoding="utf-8-sig")
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, sheet_name=sheet_name)
    else:
        raise ValueError(
            f"Unsupported candidate input format {path.suffix!r}; "
            "expected .csv, .xlsx, or .xls"
        )

    columns = (
        list(candidate_columns)
        if candidate_columns is not None
        else [
            column
            for column in DEFAULT_CANDIDATE_COLUMNS
            if column in frame.columns
        ]
    )
    if not columns:
        raise ValueError(
            "No concept-candidate column found. Expected one of: "
            f"{', '.join(DEFAULT_CANDIDATE_COLUMNS)}"
        )

    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Candidate columns not found: {missing}. "
            f"Available columns: {list(frame.columns)}"
        )

    candidates: list[str] = []
    for column in columns:
        candidates.extend(
            value.strip()
            for value in frame[column].dropna().astype(str)
            if value.strip()
        )
    return candidates


def count_candidates(candidates: Iterable[str]) -> pd.DataFrame:
    counts: Counter[str] = Counter()
    for candidate in candidates:
        if not isinstance(candidate, str):
            raise TypeError("Every concept candidate must be a string")
        normalized = normalize_surface(candidate)
        if normalized:
            counts[normalized] += 1

    rows = [
        {"concept_candidate": candidate, "count": count}
        for candidate, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    return pd.DataFrame(rows, columns=["concept_candidate", "count"])


def save_candidate_counts(
    candidate_counts: pd.DataFrame,
    output_path: str | Path,
    *,
    sheet_name: str = "candidate_counts",
) -> None:
    """Save a candidate-frequency table to CSV or Excel."""

    required_columns = {"concept_candidate", "count"}
    missing = required_columns - set(candidate_counts.columns)
    if missing:
        raise ValueError(
            f"Candidate counts are missing columns: {sorted(missing)}"
        )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        candidate_counts.to_csv(path, index=False, encoding="utf-8-sig")
    elif suffix == ".xlsx":
        candidate_counts.to_excel(path, sheet_name=sheet_name, index=False)
    else:
        raise ValueError(
            f"Unsupported candidate output format {path.suffix!r}; "
            "expected .csv or .xlsx"
        )


def build_candidate_counts(
    input_path: str | Path,
    output_path: str | Path,
    *,
    candidate_columns: Sequence[str] | None = None,
    input_sheet_name: str | int = 0,
    output_sheet_name: str = "candidate_counts",
) -> pd.DataFrame:
    """Load, count, save, and return concept-candidate frequencies."""

    candidates = load_candidates(
        input_path,
        candidate_columns=candidate_columns,
        sheet_name=input_sheet_name,
    )
    candidate_counts = count_candidates(candidates)
    save_candidate_counts(
        candidate_counts,
        output_path,
        sheet_name=output_sheet_name,
    )
    return candidate_counts
