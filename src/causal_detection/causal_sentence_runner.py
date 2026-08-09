import csv
import logging
from pathlib import Path
from typing import Protocol

from underthesea import sent_tokenize, word_tokenize

from configs.config import CACHE_DIR
from src.causal_detection.trigger_classifier import TriggerCausalClassifier
from src.data_models.causal_sentence import CausalSentence
from src.data_models.chunk import Chunk
from src.data_models.ref import SentenceRef


LOGGER = logging.getLogger(__name__)

MIN_TOKENS_PER_SENTENCE = 5

FIELDNAMES = [
    "sentence",
    "weak_label",
    "trigger",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
    "human_label",
]


class CausalClassifier(Protocol):
    def predict(self, texts: list[str]) -> list[str]: ...


class CausalSentenceRunner:
    def __init__(self, classifier: CausalClassifier | None = None):
        self.classifier = classifier or TriggerCausalClassifier()

    def process_chunk(self, chunk: Chunk) -> list[CausalSentence]:
        sentences = sent_tokenize(chunk.text)
        sentences = [s for s in sentences if len(word_tokenize(s)) >= MIN_TOKENS_PER_SENTENCE]
        if not sentences:
            return []

        labels = self.classifier.predict(sentences)
        find_triggers = getattr(self.classifier, "find_trigger_matches", None)

        rows = []
        for sentence_index, (sentence, label) in enumerate(zip(sentences, labels)):
            triggers = find_triggers(sentence) if find_triggers else []
            rows.append(CausalSentence(
                sentence=sentence,
                weak_label=label,
                trigger=triggers[0] if triggers else "",
                ref=SentenceRef(chunk=chunk.ref, sentence_index=sentence_index),
                human_label="",
            ))

        return rows

    def build_causal_sentences(
        self,
        chunks: list[Chunk],
        output_path: str | Path = CACHE_DIR,
    ) -> list[CausalSentence]:
        output_path = Path(output_path)
        causal_dir = output_path / "causal_sentences"
        causal_dir.mkdir(parents=True, exist_ok=True)
        csv_path = causal_dir / "causal_sentences.csv"

        all_rows: list[CausalSentence] = []

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()

            for chunk in chunks:
                try:
                    rows = self.process_chunk(chunk)
                except Exception as error:
                    LOGGER.error("Lỗi tại chunk %s: %s", chunk.chunk_id, error)
                    continue

                writer.writerows({
                    "sentence": row.sentence,
                    "weak_label": row.weak_label,
                    "trigger": row.trigger,
                    "chunk_id": row.chunk_id,
                    "doc_id": row.doc_id,
                    "url": row.url,
                    "sentence_index": row.sentence_index,
                    "human_label": row.human_label,
                } for row in rows)
                f.flush()

                all_rows.extend(rows)

        return all_rows
