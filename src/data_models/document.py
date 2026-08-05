from dataclasses import dataclass

@dataclass(frozen=True)
class Document:
    doc_id: str
    url: str
    path: str
    source_type: str
