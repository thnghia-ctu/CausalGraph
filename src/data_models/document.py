from dataclasses import dataclass

@dataclass(frozen=True)
class Document:
    doc_id: str
    local_path: str
    title: str | None = None
    url: str | None = None