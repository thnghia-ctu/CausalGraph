import json
import logging
from dataclasses import asdict
from pathlib import Path

from configs.config import CACHE_DIR
from src.chunking.semantic_chunker import SemanticChunker
from src.data_models.chunk import Chunk
from src.data_models.document import Document
from src.data_models.ref import ChunkRef, DocRef
import src.utils.helpers as hlp
import src.utils.text_normalization as txn


LOGGER = logging.getLogger(__name__)


def _append_jsonl(handle, chunks: list[Chunk]) -> None:
    for chunk in chunks:
        handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def load_chunks(output_path: str | Path, filename: str = "chunks.jsonl") -> list[Chunk]:
    path = Path(output_path) / "chunks" / filename
    if not path.exists():
        return []
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
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

    def chunk_document(self, document: Document, raw_dir: Path) -> list[Chunk]:
        local_path = raw_dir / document.source_type / document.path

        text = hlp.load_txt(str(local_path))
        if not text:
            return []

        text = txn.normalize_punct(text)

        chunk_texts = [chunk.text for chunk in self.chunker.chunk(text)]
        if not chunk_texts:
            return []

        doc_ref = DocRef(doc_id=document.doc_id, url=document.url)

        return [
            Chunk(
                ref=ChunkRef(doc=doc_ref, chunk_id=f"{document.doc_id}_{chunk_index:04d}"),
                chunk_index=chunk_index,
                text=chunk_text,
            )
            for chunk_index, chunk_text in enumerate(chunk_texts)
        ]

    def chunk_documents(
        self,
        documents: list[Document],
        output_path: str | Path = CACHE_DIR,
    ) -> list[Chunk]:
        output_path = Path(output_path)
        raw_dir = output_path / "raw"
        chunks_dir = output_path / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunks_path = chunks_dir / "chunks.jsonl"

        all_chunks: list[Chunk] = load_chunks(output_path)
        done_doc_ids = {chunk.doc_id for chunk in all_chunks}
        remaining_documents = [doc for doc in documents if doc.doc_id not in done_doc_ids]

        with open(chunks_path, "a", encoding="utf-8") as chunks_file:
            for document in remaining_documents:
                try:
                    chunks = self.chunk_document(document, raw_dir)
                except Exception as error:
                    LOGGER.error("Lỗi tại document %s: %s", document.doc_id, error)
                    continue

                _append_jsonl(chunks_file, chunks)
                chunks_file.flush()

                all_chunks.extend(chunks)

        return all_chunks
