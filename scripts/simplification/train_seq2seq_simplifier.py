import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.model_selection import train_test_split

from configs.config import LLM_RELATIONS_PATH, SIMPLIFIER_MODEL_DIR
from src.simplification.seq2seq_simplifier import SENTENCE_SEPARATOR, Seq2SeqSimplifier


def build_pairs(path: Path) -> list[tuple[str, str]]:
    df = pd.read_csv(path)
    grouped = df.groupby("original_sentence")["simple_sentence"].apply(list)
    return [
        (original, SENTENCE_SEPARATOR.join(simples))
        for original, simples in grouped.items()
    ]


def main():
    pairs = build_pairs(LLM_RELATIONS_PATH)
    train_pairs, eval_pairs = train_test_split(pairs, test_size=0.1, random_state=42)

    simplifier = Seq2SeqSimplifier()
    simplifier.fit(train_pairs, eval_pairs=eval_pairs, output_dir=SIMPLIFIER_MODEL_DIR)

    final_path = SIMPLIFIER_MODEL_DIR / "final"
    simplifier.save(final_path)

    print(f"Trained on {len(train_pairs)} pairs, eval on {len(eval_pairs)} -> {final_path}")


if __name__ == "__main__":
    main()
