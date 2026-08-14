import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import classification_report

from configs.config import BASE_DIR, CAUSAL_CLASSIFIER_MODEL_PATH, CAUSAL_FASTTEXT_MODEL_PATH
from src.causal_detection.embedding_classifier import EmbeddingCausalClassifier
from src.causal_detection.fasttext_classifier import FastTextCausalClassifier
from src.causal_detection.trigger_classifier import TriggerCausalClassifier
from src.causal_detection.voting_classifier import VotingCausalClassifier

TEST_SET_PATH = BASE_DIR / "data/eval/causal_test.csv"


def main():
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").dropna(subset=["sentence"])
    texts = df["sentence"].tolist()
    labels = df["label"].tolist()

    trigger = TriggerCausalClassifier()
    fasttext = FastTextCausalClassifier.load(CAUSAL_FASTTEXT_MODEL_PATH)
    embedding = EmbeddingCausalClassifier.load(CAUSAL_CLASSIFIER_MODEL_PATH)

    classifiers = {
        "Trigger": trigger,
        "FastText": fasttext,
        "Embedding": embedding,
        "Voting": VotingCausalClassifier(trigger=trigger, fasttext=fasttext, embedding=embedding),
    }

    for name, classifier in classifiers.items():
        predictions = classifier.predict(texts)
        print(f"=== {name} ===")
        print(classification_report(labels, predictions))


if __name__ == "__main__":
    main()
