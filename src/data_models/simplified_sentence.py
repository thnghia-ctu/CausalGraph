from dataclasses import dataclass

@dataclass(frozen=True)
class SimplifiedSentence:
    original_sentence: str
    simple_sentence: str
    simple_index: int
    chunk_id: str
    doc_id: str
    url: str
    sentence_index: int
