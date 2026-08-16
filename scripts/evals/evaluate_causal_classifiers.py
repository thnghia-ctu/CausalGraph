import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support

from configs.config import BASE_DIR, CAUSAL_CLASSIFIER_MODEL_PATH, CAUSAL_FASTTEXT_MODEL_PATH
from src.causal_detection.embedding_classifier import EmbeddingCausalClassifier
from src.causal_detection.fasttext_classifier import FastTextCausalClassifier
from src.causal_detection.trigger_classifier import TriggerCausalClassifier
from src.causal_detection.voting_classifier import VotingCausalClassifier

TEST_SET_PATH = BASE_DIR / "data/eval/causal_test.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/causal_classifier_metrics.csv"
POSITIVE_LABEL = "causal"


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

    rows = []
    for name, classifier in classifiers.items():
        predictions = classifier.predict(texts)
        print(f"=== {name} ===")
        print(classification_report(labels, predictions))

        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, pos_label=POSITIVE_LABEL, average="binary", zero_division=0,
        )
        rows.append({
            "Mô hình": name,
            "Accuracy": round(accuracy_score(labels, predictions), 4),
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1-score": round(f1, 4),
        })

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Đã ghi metrics vào {METRICS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
