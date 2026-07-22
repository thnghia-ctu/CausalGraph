"""VnExpress internal-search adapter."""

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..base_search_adapter import BaseSearchAdapter
from ..search_result import SearchResult


class VnExpressSearchAdapter(BaseSearchAdapter):
    """Parse the currently verified HTML search page at timkiem.vnexpress.net."""

    source_name = "vnexpress"
    domain = "vnexpress.net"
    base_url = "https://vnexpress.net/"
    search_endpoint = "https://timkiem.vnexpress.net/"
    result_selector = "#result_search article.item-news[data-url]"
    title_selector = "h3.title-news a[href]"
    link_selector = "h3.title-news a[href]"
    date_attribute = "data-publishtime"
    snippet_selector = "p.description"
    next_page_selector = "a.next-page:not(.disable)"

    def build_search_url(self, keyword: str, page_number: int) -> str:
        query = urlencode({"q": keyword, "page": page_number})
        return f"{self.search_endpoint}?{query}"

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
                    published_date_text=item.get(self.date_attribute),
                    snippet=(
                        snippet_node.get_text(" ", strip=True) if snippet_node else None
                    ),
                )
            )
        return results

    def has_next_page(self, html: str, page_number: int) -> bool:
        return BeautifulSoup(html, "html.parser").select_one(
            self.next_page_selector
        ) is not None
