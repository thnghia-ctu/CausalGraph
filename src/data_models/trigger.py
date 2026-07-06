from dataclasses import dataclass

@dataclass
class Trigger:
    start_id: int
    end_id: int
    text: str

    def token_ids(self) -> set[int]:
        """Tập id của tất cả token thuộc trigger (kể cả trigger 1 token)."""
        return set(range(self.start_id, self.end_id + 1))

    def contains(self, token_id: int) -> bool:
        return self.start_id <= token_id <= self.end_id