import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from configs.config import CAUSAL_CLASSIFIER_MODEL_PATH, CAUSAL_SENTENCES_PATH
from src.causal_detection.embedding_classifier import EmbeddingCausalClassifier

TRAIN_ROWS = 700


def main():
    df = pd.read_csv(CAUSAL_SENTENCES_PATH, sep=";").iloc[:TRAIN_ROWS]

    texts = df["sentence"].tolist()
    labels = df["weak_label"].tolist()

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    classifier = EmbeddingCausalClassifier()
    classifier.fit(train_texts, train_labels)

    predictions = classifier.predict(test_texts)
    print(classification_report(test_labels, predictions))

    classifier.save(CAUSAL_CLASSIFIER_MODEL_PATH)
    print(f"Model saved -> {CAUSAL_CLASSIFIER_MODEL_PATH}")


if __name__ == "__main__":
    main()
