import csv
import logging
from pathlib import Path

from configs.config import CACHE_DIR, SPO_TAGGER_HF_REPO_ID, SPO_TAGGER_MODEL_DIR
from src.data_models.concept_factor import ConceptFactor
from src.data_models.simplified_sentence import SimplifiedSentence
from src.data_models.spo_record import SpoRecord
from src.extraction.phobert_spo_tagger import PhoBertSpoTagger


LOGGER = logging.getLogger(__name__)

FIELDNAMES = [
    "sentence",
    "original_sentence",
    "subject",
    "predicate",
    "object",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
    "simple_index",
]


class SpoRunner:
    def __init__(self, tagger: PhoBertSpoTagger | None = None):
        if tagger is None:
            local_checkpoint = SPO_TAGGER_MODEL_DIR / "final"
            source = local_checkpoint if local_checkpoint.exists() else SPO_TAGGER_HF_REPO_ID
            tagger = PhoBertSpoTagger.load(source)
        self.tagger = tagger

    def process_sentence(self, sentence: SimplifiedSentence) -> SpoRecord | None:
        triple = self.tagger.extract(sentence.simple_sentence)
        if triple is None:
            return None

        return SpoRecord(
            sentence=sentence.simple_sentence,
            original_sentence=sentence.original_sentence,
            subject=ConceptFactor(
                factor_text=triple.subject.text.replace("_", " ") if triple.subject else "",
            ),
            predicate=triple.predicate.replace("_", " "),
            object=ConceptFactor(
                factor_text=triple.object.text.replace("_", " ") if triple.object else "",
            ),
            ref=sentence.ref,
        )

    def extract_spo(
        self,
        sentences: list[SimplifiedSentence],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SpoRecord]:
        output_path = Path(output_path)
        spo_dir = output_path / "spo"
        spo_dir.mkdir(parents=True, exist_ok=True)
        csv_path = spo_dir / "spo_relations.csv"

        all_records: list[SpoRecord] = []

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()

            for sentence in sentences:
                try:
                    record = self.process_sentence(sentence)
                except Exception as error:
                    LOGGER.error("Lỗi tại câu (doc %s): %s", sentence.doc_id, error)
                    continue

                if record is None:
                    continue

                writer.writerow({
                    "sentence": record.sentence,
                    "original_sentence": record.original_sentence,
                    "subject": record.subject.factor_text,
                    "predicate": record.predicate,
                    "object": record.object.factor_text,
                    "chunk_id": record.chunk_id,
                    "doc_id": record.doc_id,
                    "url": record.url,
                    "sentence_index": record.sentence_index,
                    "simple_index": record.simple_index,
                })
                f.flush()

                all_records.append(record)

        return all_records
