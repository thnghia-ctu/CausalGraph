import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import SPO_PREDICTIONS_PATH, SPO_RELATIONS_PATH
from src.extraction.phobert_spo_tagger import PhoBertSpoTagger

HF_REPO_ID = "thnghia-ctu/vi-spo-tagger"  # đổi thành repo của bạn


def main():
    tagger = PhoBertSpoTagger.load(HF_REPO_ID)

    with open(SPO_RELATIONS_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    results = []
    total = len(rows)
    for i, row in enumerate(rows, start=1):
        sentence = row["simple_sentence"]
        triple = tagger.extract(sentence)

        results.append({
            "simple_sentence": sentence,
            "gold_subject": row["subject_text"],
            "gold_predicate": row["predicate"],
            "gold_object": row["object_text"],
            "pred_subject": triple.subject.text.replace("_", " ") if triple and triple.subject else "",
            "pred_predicate": triple.predicate.replace("_", " ") if triple else "",
            "pred_object": triple.object.text.replace("_", " ") if triple and triple.object else "",
        })

        if i % 200 == 0 or i == total:
            print(f"[{i}/{total}]")

    SPO_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPO_PREDICTIONS_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows -> {SPO_PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()
