import json
import logging
from dataclasses import asdict
from pathlib import Path

from configs.config import CACHE_DIR, CHUNK_FILTER_THRESHOLD
from src.chunking.semantic_chunker import SemanticChunker
from src.data_models.chunk import Chunk
from src.data_models.document import Document
from src.data_models.ref import ChunkRef, DocRef
from src.filtering.semantic_filter import score_chunks
import src.utils.helpers as hlp
import src.utils.text_normalization as txn


LOGGER = logging.getLogger(__name__)


def _append_jsonl(handle, chunks: list[Chunk]) -> None:
    for chunk in chunks:
        handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def load_chunks(output_path: str | Path) -> list[Chunk]:
    filtered_path = Path(output_path) / "chunks" / "chunks_filtered.jsonl"
    if not filtered_path.exists():
        return []
    chunks = []
    with open(filtered_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            ref_data = data.pop("ref")
            doc_data = ref_data.pop("doc")
            chunks.append(Chunk(
                ref=ChunkRef(doc=DocRef(**doc_data), **ref_data),
                **data,
            ))
    return chunks


class ChunkRunner:
    def __init__(self):
        self.chunker = SemanticChunker()

    def chunk_document(self, document: Document, raw_dir: Path) -> tuple[list[Chunk], list[Chunk]]:
        local_path = raw_dir / document.source_type / document.path

        text = hlp.load_txt(str(local_path))
        if not text:
            return [], []

        text = txn.normalize_punct(text)

        chunk_texts = [chunk.text for chunk in self.chunker.chunk(text)]
        if not chunk_texts:
            return [], []

        scores = score_chunks(chunk_texts)

        doc_ref = DocRef(doc_id=document.doc_id, url=document.url)

        kept, rejected = [], []
        for chunk_index, (chunk_text, score) in enumerate(zip(chunk_texts, scores)):
            record = Chunk(
                ref=ChunkRef(doc=doc_ref, chunk_id=f"{document.doc_id}_{chunk_index:04d}"),
                chunk_index=chunk_index,
                text=chunk_text,
            )
            (kept if score > CHUNK_FILTER_THRESHOLD else rejected).append(record)

        return kept, rejected

    def chunk_documents(
        self,
        documents: list[Document],
        output_path: str | Path = CACHE_DIR,
    ) -> list[Chunk]:
        output_path = Path(output_path)
        raw_dir = output_path / "raw"
        chunks_dir = output_path / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        filtered_path = chunks_dir / "chunks_filtered.jsonl"
        rejected_path = chunks_dir / "chunks_rejected.jsonl"

        all_kept: list[Chunk] = []

        with (
            open(filtered_path, "w", encoding="utf-8") as filtered_file,
            open(rejected_path, "w", encoding="utf-8") as rejected_file,
        ):
            for document in documents:
                try:
                    kept, rejected = self.chunk_document(document, raw_dir)
                except Exception as error:
                    LOGGER.error("Lỗi tại document %s: %s", document.doc_id, error)
                    continue

                _append_jsonl(filtered_file, kept)
                _append_jsonl(rejected_file, rejected)
                filtered_file.flush()
                rejected_file.flush()

                all_kept.extend(kept)

        return all_kept
