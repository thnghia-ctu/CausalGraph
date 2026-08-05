from pathlib import Path

import pandas as pd

from src.chunking.semantic_chunker import SemanticChunker
from src.crawlers.crawl_runner import CrawlRunner
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.svo_extractor import SVOExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.filtering.semantic_filter import filter_chunks
from src.normalization.factor_normalizer import FactorNormalizer
import src.utils.text_normalization as txn
import src.utils.helpers as hlp
from configs.config import BASE_DIR, CACHE_DIR
import traceback
from src.data_models.document import Document
from src.data_models.relation import Relation
from src.data_models.normalized_factor import NormalizedFactor
import networkx as nx
from itertools import product
from src.graph.graph_visualizer import visualize_graph

class Pipeline:
    def  __init__(self):
        self.crawl_runner = CrawlRunner()
        self.chunker = SemanticChunker()
        self.relation_extractor = RelationExtractor()
        self.svo_extractor = SVOExtractor()
        # self.factor_normalizer = FactorNormalizer()
        self.factor_normalizer = FactorNormalizer.from_vocabulary_xlsx(
            BASE_DIR / "configs" / "controlled_concept_vocabulary.xlsx",
        )
        self.stats = {
            "article_count": 0,
            "all_chunks": 0,
            "accept_chunks": 0,
        }

    def crawl_data(self, urls: list[str], output_path: str | Path = CACHE_DIR) -> list[Document]:
        return self.crawl_runner.crawl_links(urls, output_path=output_path)

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
