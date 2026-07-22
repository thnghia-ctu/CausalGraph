"""Báo Nông nghiệp và Môi trường internal-search adapter."""

import time
from urllib.parse import quote, urlencode

from bs4 import BeautifulSoup

from ..base_search_adapter import BaseSearchAdapter
from ..search_result import SearchResult


class NongNghiepSearchAdapter(BaseSearchAdapter):
    """Parse the verified successor of the former nongnghiep.vn search site."""

    source_name = "nongnghiep"
    domain = "nongnghiepmoitruong.vn"
    base_url = "https://nongnghiepmoitruong.vn/"
    search_endpoint = "https://nongnghiepmoitruong.vn/"
    result_selector = "li.news-home-item.onesearch_bt"
    title_selector = "h3.main-title a[href]"
    link_selector = "h3.main-title a[href]"
    date_selector = "span.news-push-date"
    snippet_selector = "p.main-intro"
    next_page_selector = "a.load-more"

    def build_search_url(self, keyword: str, page_number: int) -> str:
        if page_number == 1:
            query = urlencode(
                {"mod": "archive", "act": "search", "search": keyword}
            )
            return f"{self.search_endpoint}?{query}"

        combined_search = quote(keyword, safe="") + "%7C%7C%7C%7C%7C%7C"
        timestamp_ms = int(time.time() * 1000)
        return (
            f"{self.base_url}loadmoreiframe/actloadsearch-search{combined_search}"
            f"-page{page_number}-date{timestamp_ms}/"
        )

    def parse_search_results(
        self,
        html: str,
        keyword: str,
        query_url: str,
        page_number: int,
    ) -> list[SearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[SearchResult] = []
        for rank, item in enumerate(soup.select(self.result_selector), start=1):
            link = item.select_one(self.link_selector)
            if link is None or not link.get("href"):
                continue
            title_node = item.select_one(self.title_selector)
            date_node = item.select_one(self.date_selector)
            snippet_node = item.select_one(self.snippet_selector)
            results.append(
                SearchResult(
                    source_name=self.source_name,
                    domain=self.domain,
                    keyword=keyword,
                    query_url=query_url,
                    page_number=page_number,
                    rank=rank,
                    title=title_node.get_text(" ", strip=True) if title_node else None,
                    url=str(link["href"]),
                    published_date_text=(
                        date_node.get_text(" ", strip=True) if date_node else None
                    ),
                    snippet=(
                        snippet_node.get_text(" ", strip=True) if snippet_node else None
                    ),
                )
            )
        return results

    def has_next_page(self, html: str, page_number: int) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        if page_number == 1:
            return soup.select_one(self.next_page_selector) is not None
        return bool(soup.select(self.result_selector))
