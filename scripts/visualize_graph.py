import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR
from src.pipeline import Pipeline
from src.utils.helpers import load_txt


def visualize():
    pipeline = Pipeline()
    relations = []

    for index in range(1, 17):
        text = load_txt(f"{BASE_DIR}/data/raw/web/{index}_text.txt")
        if text:
            relations.extend(pipeline.extract_relations(text))

    pipeline.build_graph(relations)


def main():
    visualize()


if __name__ == "__main__":
    main()
