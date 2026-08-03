import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import CAUSAL_SENTENCES_PATH
from src.causal_detection.trigger_classifier import TriggerCausalClassifier


def main():
    with open(CAUSAL_SENTENCES_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames
        rows = list(reader)

    classifier = TriggerCausalClassifier()

    total_causal = 0
    for row in rows:
        triggers = classifier.find_trigger_matches(row["sentence"])
        row["weak_label"] = "causal" if triggers else "non_causal"
        row["trigger"] = triggers[0] if triggers else ""
        total_causal += bool(triggers)

    with open(CAUSAL_SENTENCES_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Total {len(rows)} sentences, {total_causal} causal -> {CAUSAL_SENTENCES_PATH}")


if __name__ == "__main__":
    main()
