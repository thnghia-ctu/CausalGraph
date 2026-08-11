from configs.config import SPO_TAGGER_MODEL_DIR
from src.data_models.factor import Factor
from src.data_models.svo_triple import SVOTriple
from src.extraction.phobert_bio_tagger import PhoBertBioTagger, mark_span, words_and_offsets


class PhoBertSpoTagger(PhoBertBioTagger):
    """Trích bộ ba subject-predicate-object bằng PhoBERT + BIO token classification.

    Huấn luyện trực tiếp trên text thô (sentence, subject, predicate, object dạng
    chuỗi con của sentence) lấy thẳng từ CSV, không cần VnCoreNLP.
    """

    BIO_LABELS = ["O", "B-SUBJ", "I-SUBJ", "B-PRED", "I-PRED", "B-OBJ", "I-OBJ"]
    MODEL_DIR = SPO_TAGGER_MODEL_DIR

    def _build_labels(
        self, sentence: str, subject: str, predicate: str, object_: str
    ) -> tuple[list[str], list[str]] | None:
        """Trả về None nếu một span không định vị được (text gán nhãn không phải chuỗi
        con của câu). Câu không có quan hệ (cả ba cột đều rỗng) là mẫu âm hợp lệ theo
        2.4.2, giữ lại với nhãn toàn "O" thay vì bị loại bỏ. `predicate` rỗng nhưng
        subject/object có giá trị là quan hệ ngầm định (không có từ nối tường minh) —
        vẫn giữ lại, chỉ không đánh dấu PRED, khác với subject/object là bắt buộc."""
        words, offsets = words_and_offsets(sentence)
        labels = ["O"] * len(words)

        if not predicate.strip() and not subject.strip() and not object_.strip():
            return words, labels

        if predicate and not mark_span(labels, offsets, sentence, predicate, "PRED"):
            return None
        if subject and not mark_span(labels, offsets, sentence, subject, "SUBJ"):
            return None
        if object_ and not mark_span(labels, offsets, sentence, object_, "OBJ"):
            return None

        return words, labels

    def _decode(self, words: list[str], word_labels: list[str | None]) -> SVOTriple | None:
        spans: dict[str, list[int]] = {"SUBJ": [], "PRED": [], "OBJ": []}
        for i, label in enumerate(word_labels):
            if label and label != "O":
                spans[label[2:]].append(i)

        if not spans["SUBJ"] or not spans["OBJ"]:
            return None

        def to_factor(tag: str) -> Factor | None:
            ids = spans[tag]
            return Factor(text=" ".join(words[i] for i in ids), token_ids=ids) if ids else None

        predicate_text = " ".join(words[i] for i in spans["PRED"]) if spans["PRED"] else ""

        return SVOTriple(subject=to_factor("SUBJ"), predicate=predicate_text, object=to_factor("OBJ"))
