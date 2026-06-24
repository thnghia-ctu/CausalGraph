from dataclasses import dataclass, asdict
import pandas as pd

@dataclass
class DependencyToken:
    id: int
    word: str
    pos: str
    head: int
    dep: str

@dataclass
class Sentence:
    id: int
    tokens: list[DependencyToken]

def parse_dependency_dict(data: list[Sentence], out_file: str = None) -> pd.DataFrame:
    records = [
        {"sentence_id": sent.id, **asdict(tok)}
        for sent in data
        for tok in sent.tokens
    ]

    df = pd.DataFrame(records)
    if out_file:
        df.to_csv(out_file, index=False, encoding="utf-8-sig")
    return df