import csv
import logging
from pathlib import Path

from configs.config import CACHE_DIR, SIMPLIFIER_HF_REPO_ID, SIMPLIFIER_MODEL_DIR
from src.data_models.causal_sentence import CausalSentence
from src.data_models.ref import SimpleRef
from src.data_models.simplified_sentence import SimplifiedSentence
from src.simplification.seq2seq_simplifier import Seq2SeqSimplifier


LOGGER = logging.getLogger(__name__)

FIELDNAMES = [
    "original_sentence",
    "simple_sentence",
    "simple_index",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
]


class SimplifierRunner:
    def __init__(self, simplifier: Seq2SeqSimplifier | None = None):
        if simplifier is None:
            local_checkpoint = SIMPLIFIER_MODEL_DIR / "final"
            source = local_checkpoint if local_checkpoint.exists() else SIMPLIFIER_HF_REPO_ID
            simplifier = Seq2SeqSimplifier.load(source)
        self.simplifier = simplifier

    def process_causal_sentence(self, sentence: CausalSentence) -> list[SimplifiedSentence]:
        simples = self.simplifier.simplify(sentence.sentence)

        return [
            SimplifiedSentence(
                original_sentence=sentence.sentence,
                simple_sentence=simple,
                ref=SimpleRef(sentence=sentence.ref, simple_index=simple_index),
            )
            for simple_index, simple in enumerate(simples)
        ]

    def simplify_sentences(
        self,
        causal_sentences: list[CausalSentence],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SimplifiedSentence]:
        causal_only = [s for s in causal_sentences if s.weak_label == "causal"]

        output_path = Path(output_path)
        simplified_dir = output_path / "simplified"
        simplified_dir.mkdir(parents=True, exist_ok=True)
        csv_path = simplified_dir / "simplified_sentences.csv"

        all_rows: list[SimplifiedSentence] = []

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()

            for sentence in causal_only:
                try:
                    rows = self.process_causal_sentence(sentence)
                except Exception as error:
                    LOGGER.error("Lỗi tại câu (doc %s): %s", sentence.doc_id, error)
                    continue

                writer.writerows({
                    "original_sentence": row.original_sentence,
                    "simple_sentence": row.simple_sentence,
                    "simple_index": row.simple_index,
                    "chunk_id": row.chunk_id,
                    "doc_id": row.doc_id,
                    "url": row.url,
                    "sentence_index": row.sentence_index,
                } for row in rows)
                f.flush()

                all_rows.extend(rows)

        return all_rows
