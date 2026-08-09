"""Route links to the right crawler and run them as a batch."""

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
import logging

from configs.config import CACHE_DIR
from src.data_models.document import Document

from .base_crawler import BaseCrawler
from .web_crawler import WebCrawler


LOGGER = logging.getLogger(__name__)
_document_index_lock = threading.Lock()


def _append_document(index_path: Path, document: Document) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with _document_index_lock:
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(document), ensure_ascii=False) + "\n")


def load_documents(output_path: str | Path) -> list[Document]:
    index_path = Path(output_path) / "raw" / "documents.jsonl"
    if not index_path.exists():
        return []
    with open(index_path, "r", encoding="utf-8") as f:
        return [Document(**json.loads(line)) for line in f if line.strip()]


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
            from .youtube_crawler import YouTubeCrawler

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
            return crawler.run(output_path)

        except Exception as error:
            LOGGER.error("Lỗi tại link %s: %s", link, error)
            return None

    def crawl_links(
        self,
        links,
        output_path: str | Path = CACHE_DIR,
        crawler_type: str | None = None,
        delay_seconds: float | None = None,
        max_workers: int = 8,
    ) -> list[Document]:

        if delay_seconds is not None and delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")

        raw_dir = Path(output_path) / "raw"
        index_path = raw_dir / "documents.jsonl"

        crawler_classes = {self._select_crawler_class(link) for link in links}
        limiters = {
            cls.source_type: RateLimiter(
                cls.delay_seconds if delay_seconds is None else delay_seconds
            )
            for cls in crawler_classes
        }
        semaphores = {
            cls.source_type: threading.Semaphore(cls.max_concurrency or max_workers)
            for cls in crawler_classes
        }

        documents: list[Document] = []
        documents_lock = threading.Lock()

        def _crawl_one(link: str) -> None:
            crawler_class = self._select_crawler_class(link)
            source_type = crawler_class.source_type
            if crawler_type is not None and source_type != crawler_type:
                return

            doc_id = hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]
            filename = f"{doc_id}_text.txt"
            file_path = raw_dir / source_type / filename

            if file_path.exists():
                document = Document(doc_id=doc_id, url=link, path=filename, source_type=source_type)
            else:
                with semaphores[source_type]:
                    limiters[source_type].wait()
                    text = self.crawl_link(link, file_path, crawler_type=crawler_type)
                if text is None:
                    return
                document = Document(doc_id=doc_id, url=link, path=filename, source_type=source_type)
                _append_document(index_path, document)

            with documents_lock:
                documents.append(document)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(_crawl_one, links))

        return documents
