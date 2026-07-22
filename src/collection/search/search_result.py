"""Data model for one occurrence in a search result page."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchResult:
    """An article link found for one source, keyword, and result page."""

    source_name: str
    domain: str
    keyword: str
    query_url: str
    page_number: int
    rank: int | None
    title: str | None
    url: str
    published_date_text: str | None = None
    snippet: str | None = None
    normalized_url: str | None = None
    retrieved_at: str | None = None
    status: str = "collected"
