import sys
from pathlib import Path
import pandas as pd
from configs.config import BASE_DIR
from src.pipeline import Pipeline
import src.utils.helpers as hlp
from src.crawlers.crawl_runner import CrawlRunner
import traceback
import networkx as nx
from src.graph.graph_visualizer import visualize_graph


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
            crawler = CrawlRunner.create_crawler(link)
            raw_text = crawler.run(path=None, is_save=False)

            if not raw_text:
                continue

            pipeline.stats["article_count"] += 1
            relations.extend(
                pipeline.extract_relations(raw_text)
            )

        except Exception as error:
            print(f"Error at link {link}: {error}")
            traceback.print_exc()
    pd.DataFrame([pipeline.stats]).to_csv(
        BASE_DIR / "output/pipeline_stats.csv",
        index=False,
        encoding="utf-8-sig",
    )
    hlp.save_pickle(f"{BASE_DIR}data/intermediate/all_relations.pkl", relations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline.build_graph(relations, str(output_path))

def normalized_relation_visualize() -> None:
    graph = nx.DiGraph()
    df = pd.read_excel(BASE_DIR / "configs/causal_triggers.xlsx")
    triggers = set(df["trigger"].dropna().astype(str).str.strip().str.lower())
    df = pd.read_csv(BASE_DIR / "data/cache/ould_results.csv")
    relations = df.astype(object).where(df.notna(), None).to_dict("records")

    for relation in relations:
        subject = relation["subject_concept"]
        predicate = relation["predicate"]
        object_ = relation["object_concept"]

        if subject is not None and object_ is not None:# predicate.strip().lower() in triggers:
            graph.add_edge(
                subject,
                object_,
                relation=predicate,
                score=relation.get("confidence", 1.0),
            )

    output_path = BASE_DIR / "output/graph.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    visualize_graph(graph, str(output_path))

def main():
    normalized_relation_visualize()


if __name__ == "__main__":
    main()
