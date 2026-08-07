from dataclasses import replace
from pathlib import Path

import networkx as nx
import pandas as pd

from configs.config import CACHE_DIR, CONCEPT_CLUSTER_DISTANCE_THRESHOLD
from src.concept_builder.concept_clustering import (
    MIN_SENTENCE_COUNT,
    build_concept_table,
    build_graph_from_relations,
    cluster_concepts,
)
from src.data_models.concept_factor import ConceptFactor
from src.data_models.spo_record import SpoRecord
from src.graph.graph_visualizer import visualize_graph
from src.utils.text_normalization import normalize_surface

RELATION_COLUMNS = [
    "source_concept_candidate",
    "target_concept_candidate",
    "source_concept_id",
    "target_concept_id",
    "source_direction",
    "target_direction",
    "subject_text",
    "object_text",
    "predicate",
    "simple_sentence",
    "original_sentence",
    "url",
    "doc_id",
    "chunk_id",
]


class GraphRunner:
    def assign_concept_ids(
        self,
        spo_records: list[SpoRecord],
        concepts: pd.DataFrame,
    ) -> list[SpoRecord]:
        candidate_to_id = {
            member: row.concept_id
            for row in concepts.itertuples()
            for member in row.members
        }

        def tag(factor: ConceptFactor) -> ConceptFactor:
            concept_id = candidate_to_id.get(normalize_surface(factor.concept_candidate), "")
            return replace(factor, concept_id=concept_id)

        return [
            replace(record, subject=tag(record.subject), object=tag(record.object))
            for record in spo_records
        ]

    def build_relations_table(self, spo_records: list[SpoRecord]) -> pd.DataFrame:
        rows = [
            {
                "source_concept_candidate": record.subject.concept_candidate,
                "target_concept_candidate": record.object.concept_candidate,
                "source_concept_id": record.subject.concept_id or None,
                "target_concept_id": record.object.concept_id or None,
                "source_direction": record.subject.direction,
                "target_direction": record.object.direction,
                "subject_text": record.subject.factor_text,
                "object_text": record.object.factor_text,
                "predicate": record.predicate,
                "simple_sentence": record.sentence,
                "original_sentence": record.original_sentence,
                "url": record.url,
                "doc_id": record.doc_id,
                "chunk_id": record.chunk_id,
            }
            for record in spo_records
        ]

        return pd.DataFrame(rows, columns=RELATION_COLUMNS)

    def build_graph(
        self,
        spo_records: list[SpoRecord],
        output_path: str | Path = CACHE_DIR,
        distance_threshold: float = CONCEPT_CLUSTER_DISTANCE_THRESHOLD,
        min_sentence_count: int = MIN_SENTENCE_COUNT,
    ) -> nx.DiGraph:
        output_path = Path(output_path)
        graph_dir = output_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)

        graph = nx.DiGraph()
        if not spo_records:
            visualize_graph(graph, str(graph_dir / "concept_graph.html"))
            return graph

        candidates = [
            candidate
            for record in spo_records
            for candidate in (record.subject.concept_candidate, record.object.concept_candidate)
        ]
        clustered = cluster_concepts(candidates, distance_threshold=distance_threshold)
        concepts = build_concept_table(clustered)

        enriched_records = self.assign_concept_ids(spo_records, concepts)
        relations = self.build_relations_table(enriched_records)

        relations.to_csv(
            graph_dir / "relations_with_concept.csv", index=False, encoding="utf-8-sig"
        )
        concepts.to_json(
            graph_dir / "concepts.jsonl", orient="records", lines=True, force_ascii=False
        )

        graph = build_graph_from_relations(
            relations, concepts, min_sentence_count=min_sentence_count
        )
        visualize_graph(graph, str(graph_dir / "concept_graph.html"))

        return graph
