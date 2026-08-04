from configs.config import CONCEPT_STATE_TAGGER_MODEL_DIR
from src.data_models.concept_state import ConceptState
from src.data_models.factor import Factor
from src.extraction.phobert_bio_tagger import PhoBertBioTagger, mark_span, words_and_offsets


class PhoBertConceptStateTagger(PhoBertBioTagger):
    """Tách concept_candidate và state từ text của một factor (subject/object đã trích
    ở bước SPO) bằng PhoBERT + BIO token classification.

    Huấn luyện trực tiếp trên text thô (factor_text, concept_candidate, state dạng
    chuỗi con của factor_text) lấy thẳng từ CSV, không cần VnCoreNLP.
    """

    BIO_LABELS = ["O", "B-CONCEPT", "I-CONCEPT", "B-STATE", "I-STATE"]
    MODEL_DIR = CONCEPT_STATE_TAGGER_MODEL_DIR

    def _build_labels(
        self, factor_text: str, concept_candidate: str, state: str
    ) -> tuple[list[str], list[str]] | None:
        """Trả về None nếu một span không định vị được (text gán nhãn không phải chuỗi
        con của factor_text). Factor không xác định được concept lẫn state (vd. đại từ
        tham chiếu "đây", "nó") là mẫu âm hợp lệ, giữ lại với nhãn toàn "O"."""
        words, offsets = words_and_offsets(factor_text)
        labels = ["O"] * len(words)

        if not concept_candidate.strip() and not state.strip():
            return words, labels

        if concept_candidate and not mark_span(labels, offsets, factor_text, concept_candidate, "CONCEPT"):
            return None
        if state and not mark_span(labels, offsets, factor_text, state, "STATE"):
            return None

        return words, labels

    def _decode(self, words: list[str], word_labels: list[str | None]) -> ConceptState | None:
        spans: dict[str, list[int]] = {"CONCEPT": [], "STATE": []}
        for i, label in enumerate(word_labels):
            if label and label != "O":
                spans[label[2:]].append(i)

        if not spans["CONCEPT"] and not spans["STATE"]:
            return None

        concept_ids = spans["CONCEPT"]
        concept = Factor(text=" ".join(words[i] for i in concept_ids), token_ids=concept_ids) if concept_ids else None

        state_ids = spans["STATE"]
        state = " ".join(words[i] for i in state_ids) if state_ids else None

        return ConceptState(concept_candidate=concept, state=state)
