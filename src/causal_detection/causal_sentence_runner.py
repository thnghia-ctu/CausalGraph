import csv
import logging
from dataclasses import asdict
from pathlib import Path

from underthesea import sent_tokenize

from configs.config import CACHE_DIR
from src.causal_detection.trigger_classifier import TriggerCausalClassifier
from src.data_models.causal_sentence import CausalSentence
from src.data_models.chunk import Chunk


LOGGER = logging.getLogger(__name__)

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


class CausalSentenceRunner:
    def __init__(self):
        self.trigger_classifier = TriggerCausalClassifier()

    def process_chunk(self, chunk: Chunk) -> list[CausalSentence]:
        sentences = sent_tokenize(chunk.text)

        rows = []
        for sentence_index, sentence in enumerate(sentences):
            triggers = self.trigger_classifier.find_trigger_matches(sentence)
            rows.append(CausalSentence(
                sentence=sentence,
                weak_label="causal" if triggers else "non_causal",
                trigger=triggers[0] if triggers else "",
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                url=chunk.url,
                sentence_index=sentence_index,
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

                writer.writerows(asdict(row) for row in rows)
                f.flush()

                all_rows.extend(rows)

        return all_rows
