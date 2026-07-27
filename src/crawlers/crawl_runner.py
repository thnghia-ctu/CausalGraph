"""Route links to the right crawler and run them as a batch."""

import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from configs.config import BASE_DIR

from .base_crawler import BaseCrawler
from .web_crawler import WebCrawler
from .youtube_crawler import YouTubeCrawler


LOGGER = logging.getLogger(__name__)
MANIFEST_PATH = BASE_DIR / "data/raw/manifest.jsonl"
_manifest_lock = threading.Lock()


def _append_manifest(url: str, filename: str, source_type: str) -> None:
    entry = {"url": url, "filename": filename, "source_type": source_type}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _manifest_lock:
        with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class RateLimiter:
    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._next_ok_time = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_time = max(0.0, self._next_ok_time - now)
            self._next_ok_time = max(now, self._next_ok_time) + self._min_interval
        if wait_time:
            time.sleep(wait_time)


class CrawlRunner:
    """Pick a crawler for a URL and, optionally, run a batch of links."""

    @staticmethod
    def _select_crawler_class(url: str) -> type[BaseCrawler]:
        normalized_url = url.lower()

        if "youtube.com" in normalized_url or "youtu.be" in normalized_url:
            return YouTubeCrawler

        return WebCrawler

    @classmethod
    def create_crawler(cls, url: str) -> BaseCrawler:
        return cls._select_crawler_class(url)(url)

    def crawl_link(
        self,
        link: str,
        output_path: str | Path | None = None,
        crawler_type: str | None = None,
    ) -> str | None:
        
        crawler_class = self._select_crawler_class(link)
        source_type = crawler_class.source_type
        if crawler_type is not None and source_type != crawler_type:
            return None

        try:
            crawler = crawler_class(link)

            if output_path is None:
                return crawler.run(None, is_save=False)

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            text = crawler.run(output_path)
            _append_manifest(link, output_path.name, source_type)
            return text

        except Exception as error:
            LOGGER.error("Lỗi tại link %s: %s", link, error)
            return None

    def crawl_links(
        self,
        links,
        crawler_type: str | None = None,
        delay_seconds: float | None = None,
        max_workers: int = 8,
    ) -> None:

        if delay_seconds is not None and delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")

        crawler_classes = (WebCrawler, YouTubeCrawler)
        limiters = {
            cls.source_type: RateLimiter(
                cls.delay_seconds if delay_seconds is None else delay_seconds
            )
            for cls in crawler_classes
        }
        max_concurrency = {
            WebCrawler.source_type: max_workers,
            YouTubeCrawler.source_type: 1,
        }
        semaphores = {
            source_type: threading.Semaphore(cap)
            for source_type, cap in max_concurrency.items()
        }

        def _crawl_one(link: str) -> None:
            crawler_class = self._select_crawler_class(link)
            source_type = crawler_class.source_type
            if crawler_type is not None and source_type != crawler_type:
                return

            with semaphores[source_type]:
                limiters[source_type].wait()
                link_hash = hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]
                output_path = (
                    BASE_DIR / "data/raw" / source_type / f"{link_hash}_text.txt"
                )
                self.crawl_link(link, output_path, crawler_type=crawler_type)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(_crawl_one, links))
