import requests
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler
import re

class WebCrawler(BaseCrawler):
    source_type = "web"

    def fetch(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(self.url, headers=headers, timeout=10)
        # FIX encoding tại đây
        response.encoding = response.apparent_encoding
        response.raise_for_status()

        requested_url = urlparse(self.url)
        final_url = urlparse(response.url)
        requested_an_article = requested_url.path.rstrip("/") != ""
        redirected_to_homepage = final_url.path.rstrip("/") == ""

        if requested_an_article and redirected_to_homepage:
            raise ValueError(
                "URL does not resolve to an article: "
                f"{self.url} was redirected to {response.url}"
            )

        return response.text

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
       
        article_body = soup.select_one(
            '[itemprop="articleBody"], article [data-role="content"], '
            'article .detail-content'
        )

        if article_body is not None:
            article_parts = []
            title = soup.select_one(
                'h1[itemprop="headline"], h1.detail-title, article h1'
            )
            summary = soup.select_one('[data-role="sapo"], .detail-sapo')

            for element in (title, summary, article_body):
                if element is not None:
                    value = element.get_text(separator="\n", strip=True)
                    if value:
                        article_parts.append(value)

            return "\n\n".join(article_parts)

        # Generic extraction for websites without semantic article markup.
        main_text = trafilatura.extract(html, favor_precision=True, include_comments=False)

        if main_text is None:
            # Last-resort fallback if Trafilatura cannot identify main text.
            main_text = soup.get_text(separator="\n")

        return main_text

    def postprocess(self, text):
        # Normalize whitespace while preserving paragraph boundaries.
        text = re.sub(r'[ \t\r\f\v]+', ' ', text)
        text = re.sub(r' *\n *', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def save(self, text, path):
        with open(path, "w", encoding="utf-8") as f:            
            f.write(self.url + "\n\n")
            f.write(text)