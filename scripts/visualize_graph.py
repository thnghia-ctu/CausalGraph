import sys
from pathlib import Path
import pandas as pd
from configs.config import BASE_DIR
from src.pipeline import Pipeline
import src.utils.helpers as hlp
from src.crawlers.crawler_factory import CrawlerFactory
import traceback


def base_visualize():
    pipeline = Pipeline()
    relations = []

    for index in range(1, 17):
        text = hlp.load_txt(f"{BASE_DIR}/data/raw/web/{index}_text.txt")
        if text:
            relations.extend(pipeline.extract_relations(text))

    hlp.save_pickle(f"{BASE_DIR}data/intermediate/relations.pkl", relations)
    pipeline.build_graph(relations, f"{BASE_DIR}/output/concept_graph.html")

def visualize() -> None:
    pipeline = Pipeline()
    relations = []

    csv_path = BASE_DIR / "data/links/unique_links.csv"
    output_path = BASE_DIR / "output/large_concept_graph.html"

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    links = df["url"].dropna().astype(str).str.strip()

    for link in links:
        if not link:
            continue

        try:
            crawler = CrawlerFactory.create(link)
            raw_text = crawler.run(path=None, is_save=False)

            if not raw_text:
                continue

            relations.extend(
                pipeline.extract_relations(raw_text)
            )

        except Exception as error:
            print(f"Error at link {link}: {error}")
            traceback.print_exc()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline.build_graph(relations, str(output_path))

def main():
    base_visualize()


if __name__ == "__main__":
    main()
