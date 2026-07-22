"""Post-process search results and write stable CSV outputs."""

import csv
from dataclasses import asdict, replace
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from .base_search_adapter import BaseSearchAdapter
from .search_collector import CompletedPage
from .search_result import SearchResult
from .url_normalizer import normalize_url


LOGGER = logging.getLogger(__name__)
RAW_FIELDS = (
    "source_name",
    "domain",
    "keyword",
    "query_url",
    "page_number",
    "rank",
    "title",
    "url",
    "normalized_url",
    "published_date_text",
    "snippet",
    "retrieved_at",
    "status",
)
UNIQUE_FIELDS = (
    "source_name",
    "domain",
    "title",
    "url",
    "normalized_url",
    "matched_keywords",
    "first_retrieved_at",
)


def process_results(
    results: Iterable[SearchResult],
    adapters: Iterable[BaseSearchAdapter],
) -> list[SearchResult]:
    """Normalize and conservatively classify each parsed result."""
    adapter_by_source = {adapter.source_name: adapter for adapter in adapters}
    processed: list[SearchResult] = []
    for result in results:
        adapter = adapter_by_source[result.source_name]
        normalized = normalize_url(
            result.url,
            base_url=adapter.base_url,
            expected_domain=adapter.domain,
        )
        if normalized is None:
            LOGGER.warning("URL bị bỏ qua (domain/URL không hợp lệ): %s", result.url)
            processed.append(replace(result, status="invalid_url"))
        elif not adapter.is_article_url(normalized):
            LOGGER.info("URL bị bỏ qua (không phải bài viết): %s", normalized)
            processed.append(
                replace(
                    result,
                    normalized_url=normalized,
                    status="excluded_non_article",
                )
            )
        else:
            processed.append(replace(result, normalized_url=normalized))
    return processed


def build_unique_rows(raw_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate unique URLs while retaining every matching keyword."""
    grouped: dict[str, dict[str, Any]] = {}
    keywords: dict[str, list[str]] = {}
    for row in raw_rows:
        normalized = str(row.get("normalized_url") or "")
        if row.get("status") != "collected" or not normalized:
            continue
        keyword = str(row.get("keyword") or "")
        if normalized not in grouped:
            grouped[normalized] = {
                "source_name": row.get("source_name", ""),
                "domain": row.get("domain", ""),
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "normalized_url": normalized,
                "matched_keywords": "",
                "first_retrieved_at": row.get("retrieved_at", ""),
            }
            keywords[normalized] = []
        if keyword and keyword not in keywords[normalized]:
            keywords[normalized].append(keyword)
        retrieved_at = str(row.get("retrieved_at") or "")
        first = str(grouped[normalized]["first_retrieved_at"] or "")
        if retrieved_at and (not first or retrieved_at < first):
            grouped[normalized]["first_retrieved_at"] = retrieved_at
        if not grouped[normalized]["title"] and row.get("title"):
            grouped[normalized]["title"] = row["title"]

    for normalized, row in grouped.items():
        row["matched_keywords"] = "|".join(keywords[normalized])
    return list(grouped.values())


def load_completed_pages(path: Path) -> set[CompletedPage]:
    """Infer successfully parsed pages from an existing raw CSV for resume."""
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return {
            (row["source_name"], row["keyword"], int(row["page_number"]))
            for row in csv.DictReader(csv_file)
            if row.get("source_name") and row.get("keyword") and row.get("page_number")
        }


def write_search_csvs(
    results: Iterable[SearchResult],
    raw_path: Path,
    unique_path: Path,
    preserve_existing: bool = True,
) -> tuple[int, int]:
    """Atomically write raw query relations and an aggregated crawler input."""
    current_rows = [asdict(result) for result in results]
    existing_rows = _read_rows(raw_path) if preserve_existing else []
    raw_rows = _deduplicate_raw_rows([*existing_rows, *current_rows])
    unique_rows = build_unique_rows(raw_rows)
    _write_rows_atomic(raw_path, RAW_FIELDS, raw_rows)
    _write_rows_atomic(unique_path, UNIQUE_FIELDS, unique_rows)
    return len(raw_rows), len(unique_rows)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _deduplicate_raw_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("source_name") or ""),
            str(row.get("keyword") or ""),
            str(row.get("page_number") or ""),
            str(row.get("normalized_url") or row.get("url") or ""),
        )
        deduplicated[key] = {field: row.get(field, "") for field in RAW_FIELDS}
    return list(deduplicated.values())


def _write_rows_atomic(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)
