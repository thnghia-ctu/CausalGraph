from dataclasses import dataclass

@dataclass
class Factor:
    text: str
    token_ids: list[int]