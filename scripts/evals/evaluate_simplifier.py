import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR, SIMPLIFIER_VARIANTS
from src.simplification.seq2seq_simplifier import SENTENCE_SEPARATOR, Seq2SeqSimplifier
from src.simplification.simplifier_eval import score_and_save

TEST_SET_PATH = BASE_DIR / "data/eval/simplification_test.csv"
OUTPUT_DIR = BASE_DIR / "output/evals"
BATCH_SIZE = 16


def load_test_set() -> pd.DataFrame:
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").dropna(subset=["sentence", "simple_sentences"])
    return df[df["simple_sentences"].str.strip() != ""]


def load_simplifier(variant: dict) -> Seq2SeqSimplifier:
    local_checkpoint = variant["model_dir"] / "final"
    source = local_checkpoint if local_checkpoint.exists() else variant["hf_repo_id"]
    return Seq2SeqSimplifier.load(source)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=sorted(SIMPLIFIER_VARIANTS), default="vit5")
    args = parser.parse_args()
    variant = SIMPLIFIER_VARIANTS[args.model]

    predictions_output_path = OUTPUT_DIR / f"simplifier_predictions_{args.model}.csv"
    metrics_output_path = OUTPUT_DIR / f"simplifier_metrics_{args.model}.csv"

    df = load_test_set()
    originals = df["sentence"].tolist()
    gold_simples = [s.split(SENTENCE_SEPARATOR) for s in df["simple_sentences"].tolist()]

    simplifier = load_simplifier(variant)
    predicted_simples: list[list[str]] = []
    for i in range(0, len(originals), BATCH_SIZE):
        predicted_simples.extend(simplifier.simplify(originals[i : i + BATCH_SIZE]))

    score_and_save(originals, gold_simples, predicted_simples, predictions_output_path, metrics_output_path)


if __name__ == "__main__":
    main()
