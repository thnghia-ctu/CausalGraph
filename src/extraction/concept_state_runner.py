import csv
import logging
from dataclasses import replace
from pathlib import Path

from configs.config import CACHE_DIR, CONCEPT_STATE_TAGGER_HF_REPO_ID, CONCEPT_STATE_TAGGER_MODEL_DIR
from src.data_models.concept_factor import ConceptFactor
from src.data_models.spo_record import SpoRecord
from src.extraction.phobert_concept_state_tagger import PhoBertConceptStateTagger
from src.normalization.state_normalizer import StateNormalizer
from src.utils.text_normalization import normalize_surface


LOGGER = logging.getLogger(__name__)

FIELDNAMES = [
    "sentence",
    "subject_factor_text",
    "subject_concept_candidate",
    "subject_state",
    "subject_state_value",
    "subject_negated",
    "predicate",
    "object_factor_text",
    "object_concept_candidate",
    "object_state",
    "object_state_value",
    "object_negated",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
    "simple_index",
]


class ConceptStateRunner:
    def __init__(
        self,
        tagger: PhoBertConceptStateTagger | None = None,
        state_normalizer: StateNormalizer | None = None,
    ):
        if tagger is None:
            local_checkpoint = CONCEPT_STATE_TAGGER_MODEL_DIR / "final"
            source = local_checkpoint if local_checkpoint.exists() else CONCEPT_STATE_TAGGER_HF_REPO_ID
            tagger = PhoBertConceptStateTagger.load(source)
        self.tagger = tagger
        self.state_normalizer = state_normalizer or StateNormalizer()

    def tag_factor(self, factor_text: str) -> ConceptFactor:
        if not factor_text.strip():
            return ConceptFactor(factor_text=factor_text)

        result = self.tagger.extract(factor_text)
        if result is None:
            return ConceptFactor(factor_text=factor_text)

        state_text = result.state.replace("_", " ") if result.state else ""
        state_match = self.state_normalizer.normalize(normalize_surface(state_text)) if state_text else None

        return ConceptFactor(
            factor_text=factor_text,
            concept_candidate=result.concept_candidate.text.replace("_", " ") if result.concept_candidate else "",
            state=state_text,
            state_value=state_match.value if state_match else "",
            negated=state_match.state.negated if state_match else False,
        )

    def enrich_spo_record(self, record: SpoRecord) -> SpoRecord:
        return replace(
            record,
            subject=self.tag_factor(record.subject.factor_text),
            object=self.tag_factor(record.object.factor_text),
        )

    def extract_concept_states(
        self,
        spo_records: list[SpoRecord],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SpoRecord]:
        output_path = Path(output_path)
        concept_state_dir = output_path / "concept_state"
        concept_state_dir.mkdir(parents=True, exist_ok=True)
        csv_path = concept_state_dir / "concept_state_relations.csv"

        all_records: list[SpoRecord] = []

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
            writer.writeheader()

            for record in spo_records:
                try:
                    enriched = self.enrich_spo_record(record)
                except Exception as error:
                    LOGGER.error("Lỗi tại SPO record (doc %s): %s", record.doc_id, error)
                    continue

                writer.writerow({
                    "sentence": enriched.sentence,
                    "subject_factor_text": enriched.subject.factor_text,
                    "subject_concept_candidate": enriched.subject.concept_candidate,
                    "subject_state": enriched.subject.state,
                    "subject_state_value": enriched.subject.state_value,
                    "subject_negated": enriched.subject.negated,
                    "predicate": enriched.predicate,
                    "object_factor_text": enriched.object.factor_text,
                    "object_concept_candidate": enriched.object.concept_candidate,
                    "object_state": enriched.object.state,
                    "object_state_value": enriched.object.state_value,
                    "object_negated": enriched.object.negated,
                    "chunk_id": enriched.chunk_id,
                    "doc_id": enriched.doc_id,
                    "url": enriched.url,
                    "sentence_index": enriched.sentence_index,
                    "simple_index": enriched.simple_index,
                })
                f.flush()

                all_records.append(enriched)

        return all_records
