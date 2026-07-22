"""Base contract shared by newspaper search adapters."""

from abc import ABC, abstractmethod
from urllib.parse import urlparse

import requests

from .search_result import SearchResult


DEFAULT_EXCLUDED_PATH_PATTERNS = (
    "/tim-kiem",
    "/search",
    "/tag/",
    "/tags/",
    "/chu-de/",
    "/chuyen-muc/",
    "/category/",
    "/video/",
    "/photo/",
    "/podcast/",
    "/author/",
)


class BaseSearchAdapter(ABC):
    """Describe search URL construction and parsing for exactly one source."""

    source_name: str
    domain: str
    base_url: str
    excluded_path_patterns: tuple[str, ...] = ()

    @abstractmethod
    def build_search_url(self, keyword: str, page_number: int) -> str:
        """Build the URL used to fetch a search result page."""

    @abstractmethod
    def parse_search_results(
        self,
        html: str,
        keyword: str,
        query_url: str,
        page_number: int,
    ) -> list[SearchResult]:
        """Parse one HTML or JSON response into search results."""

    def fetch_page(
        self,
        session: requests.Session,
        keyword: str,
        page_number: int,
        timeout_seconds: int,
    ) -> tuple[str, str]:
        """Fetch a page; JSON-backed adapters may override this hook."""
        query_url = self.build_search_url(keyword, page_number)
        response = session.get(query_url, timeout=timeout_seconds)
        response.raise_for_status()
        return response.text, query_url

    def has_next_page(self, html: str, page_number: int) -> bool:
        """Return whether another page should be requested."""
        return False

    def is_article_url(self, url: str) -> bool:
        """Apply a conservative default filter for non-article paths."""
        path = urlparse(url).path.lower()
        patterns = DEFAULT_EXCLUDED_PATH_PATTERNS + self.excluded_path_patterns
        return not any(pattern.lower() in path for pattern in patterns)
