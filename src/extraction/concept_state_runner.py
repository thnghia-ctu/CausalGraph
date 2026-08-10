import csv
import itertools
import logging
from dataclasses import replace
from pathlib import Path

from configs.config import CACHE_DIR, CONCEPT_STATE_TAGGER_HF_REPO_ID, CONCEPT_STATE_TAGGER_MODEL_DIR
from src.data_models.concept_factor import ConceptFactor
from src.data_models.ref import ChunkRef, DocRef, SentenceRef, SimpleRef
from src.data_models.spo_record import SpoRecord
from src.extraction.phobert_concept_state_tagger import PhoBertConceptStateTagger
from src.normalization.state_normalizer import StateNormalizer
from src.utils.text_normalization import normalize_surface


LOGGER = logging.getLogger(__name__)

FIELDNAMES = [
    "sentence",
    "original_sentence",
    "subject_factor_text",
    "subject_concept_candidate",
    "subject_state",
    "subject_state_value",
    "subject_negated",
    "subject_direction",
    "predicate",
    "object_factor_text",
    "object_concept_candidate",
    "object_state",
    "object_state_value",
    "object_negated",
    "object_direction",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
    "simple_index",
]


def _factor_from_row(row: dict, prefix: str) -> ConceptFactor:
    return ConceptFactor(
        factor_text=row[f"{prefix}_factor_text"],
        concept_candidate=row[f"{prefix}_concept_candidate"],
        state=row[f"{prefix}_state"],
        state_value=row[f"{prefix}_state_value"],
        negated=row[f"{prefix}_negated"] == "True",
        direction=int(row[f"{prefix}_direction"]),
    )


def load_concept_states(output_path: str | Path = CACHE_DIR) -> list[SpoRecord]:
    csv_path = Path(output_path) / "concept_state" / "concept_state_relations.csv"
    if not csv_path.exists():
        return []

    records: list[SpoRecord] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            ref = SimpleRef(
                sentence=SentenceRef(
                    chunk=ChunkRef(
                        doc=DocRef(doc_id=row["doc_id"], url=row["url"]),
                        chunk_id=row["chunk_id"],
                    ),
                    sentence_index=int(row["sentence_index"]),
                ),
                simple_index=int(row["simple_index"]),
            )
            records.append(SpoRecord(
                sentence=row["sentence"],
                original_sentence=row.get("original_sentence", ""),
                subject=_factor_from_row(row, "subject"),
                predicate=row["predicate"],
                object=_factor_from_row(row, "object"),
                ref=ref,
            ))
    return records


DEFAULT_BATCH_SIZE = 16


class ConceptStateRunner:
    def __init__(
        self,
        tagger: PhoBertConceptStateTagger | None = None,
        state_normalizer: StateNormalizer | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        if tagger is None:
            local_checkpoint = CONCEPT_STATE_TAGGER_MODEL_DIR / "final"
            source = local_checkpoint if local_checkpoint.exists() else CONCEPT_STATE_TAGGER_HF_REPO_ID
            tagger = PhoBertConceptStateTagger.load(source)
        self.tagger = tagger
        self.state_normalizer = state_normalizer or StateNormalizer()
        self.batch_size = batch_size

    def _build_concept_factor(self, factor_text: str, result) -> ConceptFactor:
        if not factor_text.strip() or result is None:
            return ConceptFactor(factor_text=factor_text)

        state_text = result.state.replace("_", " ") if result.state else ""
        state_match = self.state_normalizer.normalize(normalize_surface(state_text)) if state_text else None

        return ConceptFactor(
            factor_text=factor_text,
            concept_candidate=result.concept_candidate.text.replace("_", " ") if result.concept_candidate else "",
            state=state_text,
            state_value=state_match.value if state_match else "",
            negated=state_match.state.negated if state_match else False,
            direction=state_match.state.direction if state_match else 0,
        )

    def tag_factors(self, factor_texts: list[str]) -> list[ConceptFactor]:
        results = self.tagger.extract_batch(factor_texts)
        return [
            self._build_concept_factor(factor_text, result)
            for factor_text, result in zip(factor_texts, results)
        ]

    def enrich_spo_records(self, records: list[SpoRecord]) -> list[SpoRecord]:
        factor_texts = []
        for record in records:
            factor_texts.append(record.subject.factor_text)
            factor_texts.append(record.object.factor_text)

        factors = self.tag_factors(factor_texts)

        return [
            replace(record, subject=factors[2 * i], object=factors[2 * i + 1])
            for i, record in enumerate(records)
        ]

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

            for batch in itertools.batched(spo_records, self.batch_size):
                try:
                    enriched_batch = self.enrich_spo_records(batch)
                except Exception as error:
                    LOGGER.error("Lỗi tại batch SPO record (doc %s): %s", batch[0].doc_id, error)
                    continue

                writer.writerows({
                    "sentence": enriched.sentence,
                    "original_sentence": enriched.original_sentence,
                    "subject_factor_text": enriched.subject.factor_text,
                    "subject_concept_candidate": enriched.subject.concept_candidate,
                    "subject_state": enriched.subject.state,
                    "subject_state_value": enriched.subject.state_value,
                    "subject_negated": enriched.subject.negated,
                    "subject_direction": enriched.subject.direction,
                    "predicate": enriched.predicate,
                    "object_factor_text": enriched.object.factor_text,
                    "object_concept_candidate": enriched.object.concept_candidate,
                    "object_state": enriched.object.state,
                    "object_state_value": enriched.object.state_value,
                    "object_negated": enriched.object.negated,
                    "object_direction": enriched.object.direction,
                    "chunk_id": enriched.chunk_id,
                    "doc_id": enriched.doc_id,
                    "url": enriched.url,
                    "sentence_index": enriched.sentence_index,
                    "simple_index": enriched.simple_index,
                } for enriched in enriched_batch)
                f.flush()

                all_records.extend(enriched_batch)

        return all_records
