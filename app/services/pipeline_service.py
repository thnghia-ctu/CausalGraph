from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.causal_detection.causal_sentence_runner import load_causal_sentences
from src.chunking.chunk_runner import load_chunks
from src.crawlers.crawl_runner import load_documents
from src.data_models.chunk import Chunk
from src.data_models.spo_record import SpoRecord
from src.extraction.concept_state_runner import load_concept_states
from src.extraction.spo_runner import load_spo_records
from src.pipeline import Pipeline
from src.simplification.simplifier_runner import load_simplified_sentences

CRAWL_STAGE = ("crawl", "Thu thập văn bản")
PROCESS_STAGES = (
    ("causal_detect", "Nhận diện câu nhân quả"),
    ("simplify", "Tách câu đơn"),
    ("spo", "Trích xuất subject-predicate-object"),
    ("concept_state", "Phân rã concept/state"),
)
STAGES = (CRAWL_STAGE, *PROCESS_STAGES)
STAGE_LABELS = dict(STAGES)

ProgressCallback = Callable[[str, int], None]


class PipelineService:
    def __init__(self):
        self._pipeline = Pipeline()

    def crawl(
        self,
        urls: list[str],
        dataset_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> list[str]:
        self._pipeline.crawl_data(urls, output_path=dataset_dir)
        docs = load_documents(dataset_dir)
        if on_progress is not None:
            on_progress("crawl", len(docs))
        return docs

    def crawl_and_chunk(
        self,
        urls: list[str],
        dataset_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> list[Chunk]:
        def report(stage_key: str, count: int) -> None:
            if on_progress is not None:
                on_progress(stage_key, count)

        self._pipeline.crawl_data(urls, output_path=dataset_dir)
        docs = load_documents(dataset_dir)
        report("crawl", len(docs))

        chunks = self._pipeline.chunk_data(docs, output_path=dataset_dir)
        report("chunk", len(chunks))

        return chunks

    def filter(self, dataset_dir: Path) -> list[Chunk]:
        chunks = load_chunks(dataset_dir)
        return self._pipeline.filter_chunks(chunks, output_path=dataset_dir)

    def process(
        self,
        dataset_dir: Path,
        on_progress: ProgressCallback | None = None,
        completed_stages: set[str] | None = None,
    ) -> list[SpoRecord]:
        completed_stages = completed_stages or set()

        def report(stage_key: str, count: int) -> None:
            if on_progress is not None:
                on_progress(stage_key, count)

        filtered_chunks = load_chunks(dataset_dir, filename="chunks_filtered.jsonl")

        if "causal_detect" in completed_stages:
            causal_sentences = load_causal_sentences(dataset_dir)
        else:
            causal_sentences = self._pipeline.detect_causal_sentences(filtered_chunks, output_path=dataset_dir)
        report("causal_detect", len(causal_sentences))

        if "simplify" in completed_stages:
            simplified = load_simplified_sentences(dataset_dir)
        else:
            simplified = self._pipeline.simplify_sentences(causal_sentences, output_path=dataset_dir)
        report("simplify", len(simplified))

        if "spo" in completed_stages:
            spo_records = load_spo_records(dataset_dir)
        else:
            spo_records = self._pipeline.extract_spo(simplified, output_path=dataset_dir)
        report("spo", len(spo_records))

        if "concept_state" in completed_stages:
            concept_states = load_concept_states(dataset_dir)
        else:
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
