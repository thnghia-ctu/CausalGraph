from src.chunking.semantic_chunker import SemanticChunker
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.filtering.semantic_filter import filter_chunks
from src.normalization.factor_normalizer import FactorNormalizer
import src.utils.text_normalization as txn
import src.utils.helpers as hlp
from configs.config import BASE_DIR
import traceback
from src.data_models.relation import Relation
import networkx as nx
from itertools import product
from src.graph.graph_visualizer import visualize_graph

class Pipeline:
    def  __init__(self):
        self.chunker = SemanticChunker()
        self.relation_extractor = RelationExtractor()
        # self.factor_normalizer = FactorNormalizer()
        self.factor_normalizer = FactorNormalizer.from_vocabulary_xlsx(
            BASE_DIR / "configs" / "controlled_concept_vocabulary.xlsx",
        )

    def prepare_text(self, text: str) -> str:
        text = txn.normalize_surface(text)
        chunks = [
            chunk.text
            for chunk in self.chunker.chunk(text)
        ]
        accepted_chunks, _ = filter_chunks(chunks)

        return " ".join(accepted_chunks)
    
    def extract_relations(self, text: str):

        prepared_text = self.prepare_text(text)
        sentences = VnCoreNLPParser.parse_text(
            prepared_text
        )
        return self.relation_extractor.extract_causal_relation(
            sentences
        )
    
    def build_graph(self, relations: list[Relation]):
        graph = nx.DiGraph()
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
            for s, t in product(source_normalized_factors, target_normalized_factors):
                source = s.concept_label
                target = t.concept_label
                if s.concept_label is None or t.concept_label is None:
                    continue
                graph.add_edge(
                    source,
                    target,
                    relation=relation.trigger.text,
                    score=relation.confidence,
                )

        visualize_graph(graph, f"{BASE_DIR}/output/concept_graph.html")
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
