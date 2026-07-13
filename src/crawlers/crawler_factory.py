from src.crawlers.base_crawler import BaseCrawler
from src.crawlers.web_crawler import WebCrawler
from src.crawlers.youtube_crawler import YouTubeCrawler

class CrawlerFactory:
    @staticmethod
    def create(url: str) -> BaseCrawler:
        normalized_url = url.lower()

        if "youtube.com" in normalized_url or "youtu.be" in normalized_url:
            return YouTubeCrawler(url)

        return WebCrawler(url)