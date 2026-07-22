"""Collect article links from publishers' internal search pages."""

from .base_search_adapter import BaseSearchAdapter
from .search_collector import SearchCollector
from .search_result import SearchResult

__all__ = ["BaseSearchAdapter", "SearchCollector", "SearchResult"]
