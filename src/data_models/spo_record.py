from dataclasses import dataclass

from src.data_models.concept_factor import ConceptFactor
from src.data_models.ref import SimpleRef

@dataclass(frozen=True)
class SpoRecord:
    sentence: str
    subject: ConceptFactor
    predicate: str
    object: ConceptFactor
    ref: SimpleRef

    @property
    def doc_id(self) -> str:
        return self.ref.doc_id

    @property
    def url(self) -> str:
        return self.ref.url

    @property
    def chunk_id(self) -> str:
        return self.ref.chunk_id

    @property
    def sentence_index(self) -> int:
        return self.ref.sentence_index

    @property
    def simple_index(self) -> int:
        return self.ref.simple_index
