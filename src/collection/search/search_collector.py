"""Orchestration of source, keyword, and search-page collection."""

from collections.abc import Collection, Iterable
from dataclasses import replace
from datetime import datetime, timezone
import logging
import time

import requests

from .base_search_adapter import BaseSearchAdapter
from .http_client import create_http_session
from .search_result import SearchResult


LOGGER = logging.getLogger(__name__)
CompletedPage = tuple[str, str, int]


class SearchCollector:
    """Collect parsed search results without writing output files."""

    def __init__(
        self,
        adapters: list[BaseSearchAdapter],
        delay_seconds: float = 2.0,
        timeout_seconds: int = 30,
        max_pages_per_keyword: int = 10,
        session: requests.Session | None = None,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        if max_pages_per_keyword < 1:
            raise ValueError("max_pages_per_keyword must be at least 1")
        self.adapters = adapters
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_pages_per_keyword = max_pages_per_keyword
        self.session = session or create_http_session()

    def collect(
        self,
        keywords: Iterable[str],
        completed_pages: Collection[CompletedPage] = (),
    ) -> list[SearchResult]:
        """Collect every configured source and keyword, isolating request errors."""
        clean_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
        completed = set(completed_pages)
        collected: list[SearchResult] = []

        for adapter in self.adapters:
            LOGGER.info("Bắt đầu nguồn %s", adapter.source_name)
            for keyword in clean_keywords:
                LOGGER.info("Tìm từ khóa %r trên %s", keyword, adapter.source_name)
                for page_number in range(1, self.max_pages_per_keyword + 1):
                    page_key = (adapter.source_name, keyword, page_number)
                    if page_key in completed:
                        LOGGER.info("Bỏ qua trang đã thu thập: %s", page_key)
                        continue
                    LOGGER.info("Lấy trang %d", page_number)
                    try:
                        html, query_url = adapter.fetch_page(
                            self.session,
                            keyword,
                            page_number,
                            self.timeout_seconds,
                        )
                        page_results = adapter.parse_search_results(
                            html, keyword, query_url, page_number
                        )
                    except requests.RequestException as error:
                        LOGGER.error(
                            "Lỗi request %s / %r / trang %d: %s",
                            adapter.source_name,
                            keyword,
                            page_number,
                            error,
                        )
                        break
                    except (ValueError, TypeError) as error:
                        LOGGER.error(
                            "Lỗi parse %s / %r / trang %d: %s",
                            adapter.source_name,
                            keyword,
                            page_number,
                            error,
                        )
                        break
                    finally:
                        if self.delay_seconds:
                            time.sleep(self.delay_seconds)

                    LOGGER.info("Lấy được %d kết quả", len(page_results))
                    if not page_results:
                        break
                    retrieved_at = datetime.now(timezone.utc).isoformat()
                    collected.extend(
                        replace(result, retrieved_at=retrieved_at)
                        for result in page_results
                    )
                    if not adapter.has_next_page(html, page_number):
                        break

        LOGGER.info("Tổng số bản ghi thô mới: %d", len(collected))
        return collected
