from dataclasses import dataclass

@dataclass(frozen=True)
class DocRef:
    doc_id: str
    url: str

@dataclass(frozen=True)
class ChunkRef:
    doc: DocRef
    chunk_id: str

    @property
    def doc_id(self) -> str:
        return self.doc.doc_id

    @property
    def url(self) -> str:
        return self.doc.url

@dataclass(frozen=True)
class SentenceRef:
    chunk: ChunkRef
    sentence_index: int

    @property
    def doc_id(self) -> str:
        return self.chunk.doc_id

    @property
    def url(self) -> str:
        return self.chunk.url

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

@dataclass(frozen=True)
class SimpleRef:
    sentence: SentenceRef
    simple_index: int

    @property
    def doc_id(self) -> str:
        return self.sentence.doc_id

    @property
    def url(self) -> str:
        return self.sentence.url

    @property
    def chunk_id(self) -> str:
        return self.sentence.chunk_id

    @property
    def sentence_index(self) -> int:
        return self.sentence.sentence_index
