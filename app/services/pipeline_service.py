from __future__ import annotations

from pathlib import Path

from src.causal_detection.causal_sentence_runner import load_causal_sentences
from src.chunking.chunk_runner import load_chunks
from src.extraction.spo_runner import load_spo_records
from src.pipeline import Pipeline
from src.simplification.simplifier_runner import load_simplified_sentences

from app.services.dataset_store import dataset_dir as get_dataset_dir, load_meta, save_meta
from app.constants.cons import (
    STATUS_FAILED,
    STATUS_INGESTING,
    STATUS_SUCCESS,
    STEP_CAUSAL_DETECTION,
    STEP_SIMPLIFICATION,
    STEP_SPO,
    STEP_CONCEPT_STATE,
)

class PipelineService:
    def __init__(self):
        self._pipeline = Pipeline()

    def process(self, dataset_id: str) -> None:
        meta = load_meta(dataset_id)

        if meta is None:
            raise ValueError(
                f"Dataset metadata not found for dataset_id: {dataset_id}"
            )

        dataset_dir = get_dataset_dir(dataset_id)

        if meta.step == STEP_CAUSAL_DETECTION:
            try:
                filtered_chunks = load_chunks(
                    dataset_dir,
                    filename="chunks_filtered.jsonl",
                )

                causal_sentences = self._pipeline.detect_causal_sentences(
                    filtered_chunks,
                    output_path=dataset_dir,
                )
                causal_count = sum(
                    sentence.weak_label == "causal"
                    for sentence in causal_sentences
                )

                meta.stage_counts["causal_detect"] = causal_count
                meta.step = STEP_SIMPLIFICATION
                meta.status = STATUS_INGESTING
                meta.error = ""

            except Exception as e:
                meta.status = STATUS_FAILED
                meta.error = str(e)
                save_meta(meta)
                return

            save_meta(meta)

        if meta.step == STEP_SIMPLIFICATION:
            try:
                causal_sentences = load_causal_sentences(dataset_dir)

                simplified = self._pipeline.simplify_sentences(
                    causal_sentences,
                    output_path=dataset_dir,
                )

                meta.stage_counts["simplify"] = len(simplified)
                meta.step = STEP_SPO
                meta.status = STATUS_INGESTING
                meta.error = ""

            except Exception as e:
                meta.status = STATUS_FAILED
                meta.error = str(e)
                save_meta(meta)
                return

            save_meta(meta)

        if meta.step == STEP_SPO:
            try:
                simplified = load_simplified_sentences(dataset_dir)

                self._pipeline.extract_spo(
                    simplified,
                    output_path=dataset_dir,
                )

                meta.step = STEP_CONCEPT_STATE
                meta.status = STATUS_INGESTING
                meta.error = ""

            except Exception as e:
                meta.status = STATUS_FAILED
                meta.error = str(e)
                save_meta(meta)
                return

            save_meta(meta)

        if meta.step == STEP_CONCEPT_STATE:
            try:
                spo_records = load_spo_records(dataset_dir)

                concept_states = self._pipeline.extract_concept_states(
                    spo_records,
                    output_path=dataset_dir,
                )

                meta.stage_counts["spo"] = len(spo_records)
                meta.stage_counts["concept_state"] = len(concept_states)
                meta.status = STATUS_SUCCESS
                meta.error = ""

            except Exception as e:
                meta.status = STATUS_FAILED
                meta.error = str(e)
                save_meta(meta)
                return

            save_meta(meta)


def get_progress(dataset_id: str) -> dict:
    meta = load_meta(dataset_id)

    if meta is None:
        return {}

    dataset_dir = get_dataset_dir(dataset_id)

    result = {
        "step": meta.step,
        "status": meta.status,
        "error": meta.error,
        "progress": {
            "current": 0,
            "goal": 0,
        },
    }

    if meta.step == STEP_CAUSAL_DETECTION:
        causal_sentences = load_causal_sentences(dataset_dir)

        causal_count = sum(
            sentence.weak_label == "causal"
            for sentence in causal_sentences
        )

        result["progress"] = {
            "current": causal_count,
            "goal": 0,
        }

    if meta.step == STEP_SIMPLIFICATION:
        simplified_sentences = load_simplified_sentences(dataset_dir)
        sentence_count = sum(
            sentence.simple_index == 0
            for sentence in simplified_sentences
        )
        result["progress"] = {
            "current": sentence_count,
            "goal": meta.stage_counts["causal_detect"],
        }

    return result
