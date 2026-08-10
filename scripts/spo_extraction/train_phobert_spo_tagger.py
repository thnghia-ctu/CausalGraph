import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sklearn.model_selection import train_test_split

from configs.config import SIMPLIFICATION_SPO_PATH, SPO_TAGGER_HF_REPO_ID, SPO_TAGGER_MODEL_DIR
from src.extraction.phobert_spo_tagger import PhoBertSpoTagger


def build_examples(path: Path) -> list[tuple[str, str, str, str]]:
    """Đọc bằng csv.DictReader thay vì pandas.read_csv: phần lớn dòng trong file này
    có thêm 2 field rỗng thừa ở cuối (vd. "...,nâng cao rõ rệt,,") khiến pandas C-engine
    báo lỗi cứng "Expected 4 fields, saw 6". DictReader gom field thừa vào key None và
    bỏ qua, không cần khai field count cố định."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            (
                (row["simple_sentence"] or "").strip(),
                (row["subject_text"] or "").strip(),
                (row["predicate"] or "").strip(),
                (row["object_text"] or "").strip(),
            )
            for row in reader
        ]


def main():
    examples = build_examples(SIMPLIFICATION_SPO_PATH)
    train_examples, eval_examples = train_test_split(examples, test_size=0.1, random_state=42)

    tagger = PhoBertSpoTagger()
    tagger.fit(train_examples, eval_examples=eval_examples, output_dir=SPO_TAGGER_MODEL_DIR)

    final_path = SPO_TAGGER_MODEL_DIR / "final"
    tagger.save(final_path)
    print(f"Trained on {len(train_examples)} examples, eval on {len(eval_examples)} -> {final_path}")

    tagger.push_to_hub(SPO_TAGGER_HF_REPO_ID)
    print(f"Pushed -> {SPO_TAGGER_HF_REPO_ID}")


if __name__ == "__main__":
    main()
