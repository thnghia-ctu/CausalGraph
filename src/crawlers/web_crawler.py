from urllib import response

import requests
import trafilatura
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
import re
class WebCrawler(BaseCrawler):

    def fetch(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(self.url, headers=headers, timeout=10)
        # FIX encoding tại đây
        response.encoding = response.apparent_encoding
        response.raise_for_status()
        return response.text

    def parse(self, html):
        # Dùng trafilatura lấy nội dung chính
        main_text = trafilatura.extract(html)

        if main_text is None:
            # fallback nếu trafilatura fail
            soup = BeautifulSoup(html, "html.parser")
            main_text = soup.get_text(separator="\n")

        return main_text

    def postprocess(self, text):
        # clean nhẹ
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def save(self, text, path):
        with open(path, "w", encoding="utf-8") as f:            
            f.write(self.url + "\n\n")
            f.write(text)