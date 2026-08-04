import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import CONCEPT_STATE_PREDICTIONS_PATH, CONCEPT_STATE_RELATIONS_PATH
from src.extraction.phobert_concept_state_tagger import PhoBertConceptStateTagger

HF_REPO_ID = "thnghia-ctu/vi-concept-state-tagger"  # đổi thành repo của bạn


def main():
    tagger = PhoBertConceptStateTagger.load(HF_REPO_ID)

    with open(CONCEPT_STATE_RELATIONS_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    results = []
    total = len(rows)
    for i, row in enumerate(rows, start=1):
        factor_text = row["factor_text"]
        result = tagger.extract(factor_text)

        results.append({
            "factor_text": factor_text,
            "gold_concept_candidate": row["concept_candidate"],
            "gold_state": row["state"],
            "pred_concept_candidate": (
                result.concept_candidate.text.replace("_", " ") if result and result.concept_candidate else ""
            ),
            "pred_state": result.state.replace("_", " ") if result and result.state else "",
        })

        if i % 200 == 0 or i == total:
            print(f"[{i}/{total}]")

    CONCEPT_STATE_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONCEPT_STATE_PREDICTIONS_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows -> {CONCEPT_STATE_PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()
