import joblib
import numpy as np
from sklearn.svm import SVC

from configs.config import CAUSAL_CLASSIFIER_MODEL_PATH
from src.utils.embedding import DEFAULT_MODEL_NAME, encode_texts, get_model


class EmbeddingCausalClassifier:
    """Phân lớp câu nhân quả dựa trên sentence embedding + SVM."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, classifier=None):
        self.model_name = model_name
        self._encoder = get_model(model_name)
        self.classifier = classifier or SVC(
            class_weight="balanced", probability=True
        )

    def _encode(self, texts: list[str]) -> np.ndarray:
        return encode_texts(texts, self._encoder, normalize_embeddings=True)

    def fit(self, texts: list[str], labels: list[str]) -> None:
        self.classifier.fit(self._encode(texts), labels)

    def predict(self, texts: list[str]) -> list[str]:
        return list(self.classifier.predict(self._encode(texts)))

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return self.classifier.predict_proba(self._encode(texts))

    def is_causal(self, text: str) -> bool:
        return self.predict([text])[0] == "causal"

    def save(self, path=CAUSAL_CLASSIFIER_MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"classifier": self.classifier, "model_name": self.model_name}, path)

    @classmethod
    def load(cls, path=CAUSAL_CLASSIFIER_MODEL_PATH) -> "EmbeddingCausalClassifier":
        data = joblib.load(path)
        return cls(model_name=data["model_name"], classifier=data["classifier"])
