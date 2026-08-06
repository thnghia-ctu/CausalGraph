from dataclasses import dataclass

from src.data_models.ref import ChunkRef

@dataclass(frozen=True)
class Chunk:
    ref: ChunkRef
    chunk_index: int
    text: str

    @property
    def doc_id(self) -> str:
        return self.ref.doc_id

    @property
    def url(self) -> str:
        return self.ref.url

    @property
    def chunk_id(self) -> str:
        return self.ref.chunk_id
