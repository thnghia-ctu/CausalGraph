from collections import Counter

from src.causal_detection.embedding_classifier import EmbeddingCausalClassifier
from src.causal_detection.fasttext_classifier import FastTextCausalClassifier
from src.causal_detection.trigger_classifier import TriggerCausalClassifier


class VotingCausalClassifier:
    """Phân lớp câu nhân quả bằng bỏ phiếu đa số giữa Trigger, FastText và Embedding."""

    def __init__(self, trigger=None, fasttext=None, embedding=None):
        self.trigger = trigger or TriggerCausalClassifier()
        self.fasttext = fasttext or FastTextCausalClassifier.load()
        self.embedding = embedding or EmbeddingCausalClassifier.load()

    def predict(self, texts: list[str]) -> list[str]:
        votes = zip(
            self.trigger.predict(texts),
            self.fasttext.predict(texts),
            self.embedding.predict(texts),
        )
        return [Counter(vote).most_common(1)[0][0] for vote in votes]
