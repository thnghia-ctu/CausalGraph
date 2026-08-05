from dataclasses import dataclass

@dataclass(frozen=True)
class CausalSentence:
    sentence: str
    weak_label: str
    trigger: str
    chunk_id: str
    doc_id: str
    url: str
    sentence_index: int
    human_label: str
