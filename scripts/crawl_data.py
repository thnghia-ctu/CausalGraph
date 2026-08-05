import logging

import pandas as pd

from configs.config import BASE_DIR, UNIQUE_LINKS_PATH
from src.crawlers.crawl_runner import CrawlRunner


def load_links(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df["url"].dropna().astype(str).str.strip().tolist()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    links = load_links(UNIQUE_LINKS_PATH)
    CrawlRunner().crawl_links(links, output_path=BASE_DIR / "data", crawler_type="web")  # Change to "web" for web crawling


if __name__ == "__main__":
    main()
