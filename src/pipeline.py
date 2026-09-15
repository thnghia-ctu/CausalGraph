from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.causal_detection.causal_sentence_runner import CausalSentenceRunner
    from src.extraction.concept_state_runner import ConceptStateRunner
    from src.extraction.spo_runner import SpoRunner
    from src.filtering.chunk_filter_runner import ChunkFilterRunner
    from src.simplification.simplifier_runner import SimplifierRunner

from src.chunking.chunk_runner import ChunkRunner
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT
from src.crawlers.crawl_runner import CrawlRunner
from src.graph.graph_runner import GraphRunner
from configs.config import CACHE_DIR, CONCEPT_CLUSTER_DISTANCE_THRESHOLD
from src.data_models.causal_sentence import CausalSentence
from src.data_models.chunk import Chunk
from src.data_models.document import Document
from src.data_models.simplified_sentence import SimplifiedSentence
from src.data_models.spo_record import SpoRecord
import networkx as nx

class Pipeline:
    @cached_property
    def crawl_runner(self) -> CrawlRunner:
        return CrawlRunner()

    @cached_property
    def chunk_runner(self) -> ChunkRunner:
        return ChunkRunner()

    @cached_property
    def chunk_filter_runner(self) -> "ChunkFilterRunner":
        from src.filtering.chunk_filter_runner import ChunkFilterRunner

        return ChunkFilterRunner()

    @cached_property
    def causal_sentence_runner(self) -> "CausalSentenceRunner":
        from src.causal_detection.causal_sentence_runner import CausalSentenceRunner
        from src.causal_detection.voting_classifier import VotingCausalClassifier

        return CausalSentenceRunner(classifier=VotingCausalClassifier())

    @cached_property
    def simplifier_runner(self) -> "SimplifierRunner":
        from src.simplification.simplifier_runner import SimplifierRunner

        return SimplifierRunner()

    @cached_property
    def spo_runner(self) -> "SpoRunner":
        from src.extraction.spo_runner import SpoRunner

        return SpoRunner()

    @cached_property
    def concept_state_runner(self) -> "ConceptStateRunner":
        from src.extraction.concept_state_runner import ConceptStateRunner

        return ConceptStateRunner()

    @cached_property
    def graph_runner(self) -> GraphRunner:
        return GraphRunner()

    def crawl_data(self, urls: list[str], output_path: str | Path = CACHE_DIR) -> list[Document]:
        return self.crawl_runner.crawl_links(urls, output_path=output_path)

    def chunk_data(self, documents: list[Document], output_path: str | Path = CACHE_DIR) -> list[Chunk]:
        return self.chunk_runner.chunk_documents(documents, output_path=output_path)

    def filter_chunks(self, chunks: list[Chunk], output_path: str | Path = CACHE_DIR) -> list[Chunk]:
        return self.chunk_filter_runner.filter_chunks(chunks, output_path=output_path)

    def detect_causal_sentences(
        self,
        chunks: list[Chunk],
        output_path: str | Path = CACHE_DIR,
    ) -> list[CausalSentence]:
        return self.causal_sentence_runner.build_causal_sentences(chunks, output_path=output_path)

    def simplify_sentences(
        self,
        causal_sentences: list[CausalSentence],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SimplifiedSentence]:
        return self.simplifier_runner.simplify_sentences(causal_sentences, output_path=output_path)

    def extract_spo(
        self,
        simplified_sentences: list[SimplifiedSentence],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SpoRecord]:
        return self.spo_runner.extract_spo(simplified_sentences, output_path=output_path)

    def extract_concept_states(
        self,
        spo_records: list[SpoRecord],
        output_path: str | Path = CACHE_DIR,
    ) -> list[SpoRecord]:
        return self.concept_state_runner.extract_concept_states(spo_records, output_path=output_path)

    def build_concept_graph(
        self,
        spo_records: list[SpoRecord],
        output_path: str | Path = CACHE_DIR,
        distance_threshold: float = CONCEPT_CLUSTER_DISTANCE_THRESHOLD,
        min_sentence_count: int = MIN_SENTENCE_COUNT,
    ) -> nx.DiGraph:
        return self.graph_runner.build_graph(
            spo_records,
            output_path=output_path,
            distance_threshold=distance_threshold,
            min_sentence_count=min_sentence_count,
        )

