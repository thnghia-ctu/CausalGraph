import requests
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler

class WebCrawler(BaseCrawler):

    def fetch(self):
        response = requests.get(self.url)
        return response.text

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        return text

    def save(self, text, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)