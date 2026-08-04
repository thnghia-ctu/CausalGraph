from gliner import GLiNER

DEFAULT_MODEL_NAME = "gliner-community/gliner_small-v2.5"
DEFAULT_LABELS = ["Giải pháp/Công nghệ", "Tác động/Hành động", "Mục tiêu/Đối tượng"]


class GlinerExtractor:
    """Trích span theo vai trò (giải pháp/tác động/mục tiêu) bằng GLiNER (zero-shot NER)."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, labels: list[str] | None = None):
        self.model = GLiNER.from_pretrained(model_name)
        self.labels = labels or DEFAULT_LABELS

    def extract(self, text: str, labels: list[str] | None = None) -> list[dict]:
        return self.model.predict_entities(text, labels or self.labels)
