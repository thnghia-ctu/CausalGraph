from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import streamlit as st

from configs.config import CONCEPT_CLUSTER_DISTANCE_THRESHOLD
from services.pipeline_service import get_pipeline_service
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT
from src.data_models.spo_record import SpoRecord
from src.extraction.concept_state_runner import load_concept_states


@dataclass(frozen=True)
class GraphViewConfig:
    distance_threshold: float = CONCEPT_CLUSTER_DISTANCE_THRESHOLD
    min_sentence_count: int = MIN_SENTENCE_COUNT


@st.cache_data(show_spinner="Đang tải dữ liệu quan hệ...")
def load_spo_records(dataset_dir_str: str, cache_bust: float) -> list[SpoRecord]:
    return load_concept_states(dataset_dir_str)


@st.cache_data(show_spinner="Đang gom nhóm concept và dựng đồ thị...")
def build_graph(
    spo_records: list[SpoRecord],
    dataset_dir_str: str,
    config: GraphViewConfig,
) -> nx.DiGraph:
    service = get_pipeline_service()
    return service.build_graph(
        spo_records,
        Path(dataset_dir_str),
        distance_threshold=config.distance_threshold,
        min_sentence_count=config.min_sentence_count,
    )
