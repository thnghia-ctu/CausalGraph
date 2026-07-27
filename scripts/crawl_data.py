import logging

from configs.config import BASE_DIR
from src.crawlers.crawl_runner import CrawlRunner


def load_links(path):
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    links_path = BASE_DIR / "data/raw/links.txt"
    links = load_links(links_path)
    CrawlRunner().crawl_links(links, crawler_type="web")  # Change to "web" for web crawling


if __name__ == "__main__":
    main()
