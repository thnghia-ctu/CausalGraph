from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.causal_detection.causal_sentence_runner import CausalSentenceRunner
    from src.extraction.concept_state_runner import ConceptStateRunner
    from src.extraction.spo_runner import SpoRunner
    from src.filtering.chunk_filter_runner import ChunkFilterRunner
    from src.simplification.simplifier_runner import SimplifierRunner

from src.chunking.chunk_runner import ChunkRunner
from src.chunking.semantic_chunker import SemanticChunker
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT
from src.crawlers.crawl_runner import CrawlRunner
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.svo_extractor import SVOExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.filtering.semantic_filter import filter_chunks
from src.graph.graph_runner import GraphRunner
from src.normalization.factor_normalizer import FactorNormalizer
import src.utils.text_normalization as txn
import src.utils.helpers as hlp
from configs.config import BASE_DIR, CACHE_DIR, CONCEPT_CLUSTER_DISTANCE_THRESHOLD
import traceback
from src.data_models.causal_sentence import CausalSentence
from src.data_models.chunk import Chunk
from src.data_models.document import Document
from src.data_models.relation import Relation
from src.data_models.normalized_factor import NormalizedFactor
from src.data_models.simplified_sentence import SimplifiedSentence
from src.data_models.spo_record import SpoRecord
import networkx as nx
from itertools import product
from src.graph.graph_visualizer import visualize_graph

class Pipeline:
    def  __init__(self):
        self.stats = {
            "article_count": 0,
            "all_chunks": 0,
            "accept_chunks": 0,
        }

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
    def chunker(self) -> SemanticChunker:
        return SemanticChunker()

    @cached_property
    def relation_extractor(self) -> RelationExtractor:
        return RelationExtractor()

    @cached_property
    def svo_extractor(self) -> SVOExtractor:
        return SVOExtractor()

    @cached_property
    def factor_normalizer(self) -> FactorNormalizer:
        return FactorNormalizer.from_vocabulary_xlsx(
            BASE_DIR / "configs" / "controlled_concept_vocabulary.xlsx",
        )

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

    def prepare_text(self, text: str) -> str:
        chunks = [
            chunk.text
            for chunk in self.chunker.chunk(text)
        ]
        accepted_chunks, _ = filter_chunks(chunks)

        self.stats["all_chunks"] += len(chunks)
        self.stats["accept_chunks"] += len(accepted_chunks)

        return " ".join(accepted_chunks)
    
    def extract_relations(self, text: str):

        prepared_text = self.prepare_text(text)
        sentences = VnCoreNLPParser.parse_text(
            prepared_text
        )
        return [self.svo_extractor.extract(sentence) for sentence in sentences]
        # return self.relation_extractor.extract_causal_relation(
        #     sentences
        # )

    @staticmethod
    def save_relations(relations: list[Relation], out_path: str | Path) -> None:
        """Lưu relations dưới dạng CSV hoặc XLSX theo đuôi file."""
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for relation in relations:
            tokens = relation.sentence.tokens if relation.sentence else []
            rows.append({
                "pattern": relation.relationship,
                "source": relation.source.text if relation.source else None,
                "trigger": relation.trigger.text,
                "target": relation.target.text if relation.target else None,
                "sentence": " ".join(token.word for token in tokens),
            })
        frame = pd.DataFrame(rows, columns=(
            "pattern", "source", "trigger",
            "target", "sentence",
        ))

        if path.suffix.casefold() == ".csv":
            frame.to_csv(path, index=False, encoding="utf-8-sig")
        elif path.suffix.casefold() == ".xlsx":
            frame.to_excel(path, index=False, sheet_name="relations")
        else:
            raise ValueError("out_path must end with .csv or .xlsx")
        
    @staticmethod
    def save_candidates(
        factors: list[NormalizedFactor],
        out_path: str | Path,
    ) -> None:
        """Lưu các factor chuẩn hóa dưới dạng CSV hoặc XLSX."""
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame([
            {
                "normalized_text": factor.normalized_text,
                "state": factor.state if factor.state else None,
                "concept_candidate": factor.concept_candidate,
                "concept_label": factor.concept_label,
            }
            for factor in factors
        ], columns=(
            "normalized_text", "state", "concept_candidate", "concept_label",
        ))

        if path.suffix.casefold() == ".csv":
            frame.to_csv(path, index=False, encoding="utf-8-sig")
        elif path.suffix.casefold() == ".xlsx":
            frame.to_excel(path, index=False, sheet_name="candidates")
        else:
            raise ValueError("out_path must end with .csv or .xlsx")

    
    def build_graph(self, relations: list[Relation], out_path):
        graph = nx.DiGraph()
        all_normalized_factors = []
        for relation in relations:
            if (
                relation.source is None
                or relation.target is None
                or relation.sentence is None
            ):
                continue

            source_normalized_factors = self.factor_normalizer.normalize_factor(
                relation.source,
                relation.sentence,
            )
            target_normalized_factors = self.factor_normalizer.normalize_factor(
                relation.target,
                relation.sentence,
            )

            all_normalized_factors.extend(source_normalized_factors)
            all_normalized_factors.extend(target_normalized_factors)

            for s, t in product(source_normalized_factors, target_normalized_factors):
                source = s.concept_label
                target = t.concept_label
                if s.concept_label is None or t.concept_label is None:
                    continue
                graph.add_edge(
                    source,
                    target,
                    relation=(
                        f"{s.state.expression + ' - ' if s.state is not None else ''}"
                        f"{relation.trigger.text}"
                        f"{' - ' + t.state.expression if t.state is not None else ''}"
                    ),
                    score=relation.confidence,
                )

        # save
        self.save_relations(relations, f"{BASE_DIR}/output/large_extracted_relations.csv")
        self.save_candidates(all_normalized_factors, f"{BASE_DIR}/output/large_candidates.csv")

        visualize_graph(graph, out_path)
        return graph                 
                
    
    def process_document(
        self,
        text: str,
        document_id: str,
    ):
        relations = self.extract_relations(text)

        return {
            "document_id": document_id,
            "relations": relations,
        }
    
    def run(self, candidate_length_limit: int):
        if candidate_length_limit <= 0:
            raise ValueError("candidate_length_limit must be greater than 0")

        candidates = []
        for i in range(1, 17):
            try:
                text = hlp.load_txt(f"{BASE_DIR}/data/raw/web/{i}_text.txt")
                if not text:
                    continue
                relations = self.extract_relations(text)
                for relation in relations:
                    for factor in (relation["re"].source, relation["re"].target):
                        if factor is None:
                            continue
                        normalized_factors = self.factor_normalizer.normalize_factor(
                            factor, relation["sentence"]
                        )
                        for normalized_factor in normalized_factors:
                            candidate = normalized_factor.concept_candidate
                            if candidate is not None and len(candidate) < candidate_length_limit:
                                candidates.append(candidate)
            except Exception as e:
                print(f"Error processing file {i}: {e}")
                traceback.print_exc()
                continue
        
        return candidates
