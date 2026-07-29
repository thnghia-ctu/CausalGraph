from dataclasses import dataclass

@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    url: str
    chunk_index: int
    text: str
