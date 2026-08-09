import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import CAUSAL_CLASSIFIER_HF_REPO_ID, CAUSAL_FASTTEXT_HF_REPO_ID
from src.causal_detection.embedding_classifier import EmbeddingCausalClassifier
from src.causal_detection.fasttext_classifier import FastTextCausalClassifier


def main():
    FastTextCausalClassifier.load().push_to_hub(CAUSAL_FASTTEXT_HF_REPO_ID)
    print(f"Pushed fastText -> {CAUSAL_FASTTEXT_HF_REPO_ID}")

    EmbeddingCausalClassifier.load().push_to_hub(CAUSAL_CLASSIFIER_HF_REPO_ID)
    print(f"Pushed SVM -> {CAUSAL_CLASSIFIER_HF_REPO_ID}")


if __name__ == "__main__":
    main()
