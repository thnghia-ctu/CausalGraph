import itertools
import json
import logging
from dataclasses import asdict
from pathlib import Path

from configs.config import CACHE_DIR, CHUNK_FILTER_THRESHOLD
from src.data_models.chunk import Chunk
from src.filtering.knowledge_base_store import load_knowledge_base
from src.filtering.scorer import Scorer
import src.utils.embedding as emb


LOGGER = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 64


def _append_jsonl(handle, chunks: list[Chunk]) -> None:
    for chunk in chunks:
        handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


class ChunkFilterRunner:
    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE):
        self.batch_size = batch_size

    def filter_chunks(
        self,
        chunks: list[Chunk],
        output_path: str | Path = CACHE_DIR,
    ) -> list[Chunk]:
        output_path = Path(output_path)
        chunks_dir = output_path / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        filtered_path = chunks_dir / "chunks_filtered.jsonl"
        rejected_path = chunks_dir / "chunks_rejected.jsonl"

        knowledge_base = load_knowledge_base(output_path)
        scorer = Scorer(
            emb.encode_texts(knowledge_base["lexicon"]),
            emb.encode_texts(knowledge_base["query"]),
        )
        threshold = knowledge_base.get("threshold", CHUNK_FILTER_THRESHOLD)

        all_kept: list[Chunk] = []

        with (
            open(filtered_path, "w", encoding="utf-8") as filtered_file,
            open(rejected_path, "w", encoding="utf-8") as rejected_file,
        ):
            for batch in itertools.batched(chunks, self.batch_size):
                try:
                    scores = scorer.score([chunk.text for chunk in batch])
                except Exception as error:
                    LOGGER.error("Lỗi tại batch chunk (doc %s): %s", batch[0].doc_id, error)
                    continue

                kept, rejected = [], []
                for chunk, score in zip(batch, scores):
                    (kept if score > threshold else rejected).append(chunk)

                _append_jsonl(filtered_file, kept)
                _append_jsonl(rejected_file, rejected)
                filtered_file.flush()
                rejected_file.flush()

                all_kept.extend(kept)

        return all_kept
