from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.data_models.spo_record import SpoRecord
from src.pipeline import Pipeline

STAGES = (
    ("crawl", "Thu thập văn bản"),
    ("chunk", "Phân đoạn văn bản"),
    ("causal_detect", "Nhận diện câu nhân quả"),
    ("simplify", "Tách câu đơn"),
    ("spo", "Trích xuất subject-predicate-object"),
    ("concept_state", "Phân rã concept/state"),
)
STAGE_LABELS = dict(STAGES)

ProgressCallback = Callable[[str, int], None]


class PipelineService:
    def __init__(self):
        self._pipeline = Pipeline()

    def ingest(
        self,
        urls: list[str],
        dataset_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> list[SpoRecord]:
        def report(stage_key: str, count: int) -> None:
            if on_progress is not None:
                on_progress(stage_key, count)

        docs = self._pipeline.crawl_data(urls, output_path=dataset_dir)
        report("crawl", len(docs))

        chunks = self._pipeline.chunk_data(docs, output_path=dataset_dir)
        report("chunk", len(chunks))

        causal_sentences = self._pipeline.detect_causal_sentences(chunks, output_path=dataset_dir)
        report("causal_detect", len(causal_sentences))

        simplified = self._pipeline.simplify_sentences(causal_sentences, output_path=dataset_dir)
        report("simplify", len(simplified))

        spo_records = self._pipeline.extract_spo(simplified, output_path=dataset_dir)
        report("spo", len(spo_records))

        concept_states = self._pipeline.extract_concept_states(spo_records, output_path=dataset_dir)
        report("concept_state", len(concept_states))

        return concept_states

    def build_graph(
        self,
        spo_records: list[SpoRecord],
        dataset_dir: Path,
        distance_threshold: float,
        min_sentence_count: int,
    ):
        return self._pipeline.build_concept_graph(
            spo_records,
            output_path=dataset_dir,
            distance_threshold=distance_threshold,
            min_sentence_count=min_sentence_count,
        )


@st.cache_resource(show_spinner="Đang khởi tạo pipeline (load model lần đầu, có thể mất vài phút)...")
def get_pipeline_service() -> PipelineService:
    return PipelineService()
