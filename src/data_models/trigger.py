from dataclasses import dataclass

@dataclass
class Trigger:
    start_id: int
    end_id: int
    text: str