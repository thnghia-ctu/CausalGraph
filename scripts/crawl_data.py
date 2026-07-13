from collections import defaultdict

from configs.config import BASE_DIR
from src.crawlers.crawler_factory import CrawlerFactory


def load_links(path):
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def crawl_links(links, crawler_type=None):
    counters = defaultdict(int)
    for link in links:
        try:
            crawler = CrawlerFactory.create(link)
            source_type = crawler.source_type
            if crawler_type is not None and source_type != crawler_type:
                continue
            output_index = counters[source_type] + 1

            output_path = (
                BASE_DIR
                / "data/raw"
                / source_type
                / f"{output_index}_text.txt"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            crawler.run(output_path)
            counters[source_type] = output_index

        except Exception as error:
            print(f"Error at link {link}: {error}")

def main():
    links_path = BASE_DIR / "data/raw/links.txt"
    links = load_links(links_path)
    crawl_links(links, crawler_type="web")  # Change to "web" for web crawling


if __name__ == "__main__":
    main()
