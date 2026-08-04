import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import CAUSAL_SENTENCES_PATH
from src.causal_detection.fasttext_classifier import FastTextCausalClassifier


def main():
    with open(CAUSAL_SENTENCES_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames
        rows = list(reader)

    if "fasttext_label" not in fieldnames:
        fieldnames = [*fieldnames, "fasttext_label"]

    classifier = FastTextCausalClassifier.load()
    predictions = classifier.predict([row["sentence"] for row in rows])

    for row, prediction in zip(rows, predictions):
        row["fasttext_label"] = prediction

    with open(CAUSAL_SENTENCES_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    total_causal = sum(1 for p in predictions if p == "causal")
    print(f"Total {len(rows)} sentences, {total_causal} causal (fasttext_label) -> {CAUSAL_SENTENCES_PATH}")


if __name__ == "__main__":
    main()
