import tempfile
from pathlib import Path

import fasttext
import numpy as np
from underthesea import word_tokenize

from configs.config import CAUSAL_FASTTEXT_MODEL_PATH
from src.utils.hub import push_file_to_hub

_LABEL_PREFIX = "__label__"


class FastTextCausalClassifier:
    """Phân lớp câu nhân quả bằng fastText supervised text classification."""

    def __init__(self, model=None, classes: list[str] | None = None, **train_params):
        self.model = model
        self.classes_ = classes or []
        self.train_params = train_params

    @staticmethod
    def _preprocess(text: str) -> str:
        return word_tokenize(text, format="text")

    def fit(self, texts: list[str], labels: list[str]) -> None:
        self.classes_ = sorted(set(labels))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            for text, label in zip(texts, labels):
                f.write(f"{_LABEL_PREFIX}{label} {self._preprocess(text)}\n")
            train_path = f.name

        params = {"epoch": 25, "lr": 0.5, "wordNgrams": 2, "verbose": 0, **self.train_params}
        self.model = fasttext.train_supervised(input=train_path, **params)
        Path(train_path).unlink()

    def predict(self, texts: list[str]) -> list[str]:
        labels, _ = self.model.predict([self._preprocess(t) for t in texts])
        return [lbl[0][len(_LABEL_PREFIX):] for lbl in labels]

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        proba = np.zeros((len(texts), len(self.classes_)))
        labels_batch, probs_batch = self.model.predict(
            [self._preprocess(t) for t in texts], k=len(self.classes_)
        )
        for i, (labels, probs) in enumerate(zip(labels_batch, probs_batch)):
            for label, prob in zip(labels, probs):
                class_name = label[len(_LABEL_PREFIX):]
                proba[i, self.classes_.index(class_name)] = prob
        return proba

    def is_causal(self, text: str) -> bool:
        return self.predict([text])[0] == "causal"

    def save(self, path=CAUSAL_FASTTEXT_MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path))

    @classmethod
    def load(cls, path=CAUSAL_FASTTEXT_MODEL_PATH) -> "FastTextCausalClassifier":
        model = fasttext.load_model(str(path))
        classes = sorted(
            label[len(_LABEL_PREFIX):] for label in model.get_labels()
        )
        return cls(model=model, classes=classes)

    def push_to_hub(self, repo_id: str, path=CAUSAL_FASTTEXT_MODEL_PATH) -> None:
        push_file_to_hub(repo_id, path)
