import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sklearn.model_selection import train_test_split

from configs.config import CONCEPT_STATE_RELATIONS_PATH, CONCEPT_STATE_TAGGER_MODEL_DIR
from src.extraction.phobert_concept_state_tagger import PhoBertConceptStateTagger


def build_examples(path: Path) -> list[tuple[str, str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            (
                (row["factor_text"] or "").strip(),
                (row["concept_candidate"] or "").strip(),
                (row["state"] or "").strip(),
            )
            for row in reader
        ]


def main():
    examples = build_examples(CONCEPT_STATE_RELATIONS_PATH)
    train_examples, eval_examples = train_test_split(examples, test_size=0.1, random_state=42)

    tagger = PhoBertConceptStateTagger()
    tagger.fit(train_examples, eval_examples=eval_examples, output_dir=CONCEPT_STATE_TAGGER_MODEL_DIR)

    final_path = CONCEPT_STATE_TAGGER_MODEL_DIR / "final"
    tagger.save(final_path)

    print(f"Trained on {len(train_examples)} examples, eval on {len(eval_examples)} -> {final_path}")


if __name__ == "__main__":
    main()
