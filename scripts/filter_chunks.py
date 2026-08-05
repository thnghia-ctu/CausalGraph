import json
import sys
import traceback
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import (
    BASE_DIR,
    CHUNK_FILTER_THRESHOLD,
    FILTERED_CHUNKS_PATH,
    REJECTED_CHUNKS_PATH,
)
from src.chunking.semantic_chunker import SemanticChunker
from src.crawlers.crawl_runner import load_documents
from src.data_models.chunk import Chunk
from src.data_models.document import Document
from src.filtering.semantic_filter import score_chunks
import src.utils.helpers as hlp


def append_jsonl(handle, chunks: list[Chunk]) -> None:
    for chunk in chunks:
        handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")


def process_document(document: Document, chunker: SemanticChunker) -> tuple[list[Chunk], list[Chunk]]:
    local_path = BASE_DIR / "data/raw" / document.source_type / document.path

    text = hlp.load_txt(str(local_path))
    if not text:
        return [], []

    chunk_texts = [chunk.text for chunk in chunker.chunk(text)]
    if not chunk_texts:
        return [], []

    scores = score_chunks(chunk_texts)

    kept, rejected = [], []
    for chunk_index, (chunk_text, score) in enumerate(zip(chunk_texts, scores)):
        record = Chunk(
            chunk_id=f"{document.doc_id}_{chunk_index:04d}",
            doc_id=document.doc_id,
            url=document.url,
            chunk_index=chunk_index,
            text=chunk_text,
        )
        (kept if score > CHUNK_FILTER_THRESHOLD else rejected).append(record)

    return kept, rejected


def main():
    chunker = SemanticChunker()
    documents = load_documents(BASE_DIR / "data")

    FILTERED_CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REJECTED_CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_kept = 0
    total_rejected = 0

    with (
        open(FILTERED_CHUNKS_PATH, "w", encoding="utf-8") as kept_file,
        open(REJECTED_CHUNKS_PATH, "w", encoding="utf-8") as rejected_file,
    ):
        for doc_number, document in enumerate(documents, start=1):
            try:
                kept, rejected = process_document(document, chunker)
            except Exception as e:
                print(f"Error processing {document.path}: {e}")
                traceback.print_exc()
                continue

            append_jsonl(kept_file, kept)
            append_jsonl(rejected_file, rejected)
            kept_file.flush()
            rejected_file.flush()

            total_kept += len(kept)
            total_rejected += len(rejected)
            print(f"[{doc_number}/{len(documents)}] {document.path}: {len(kept)}/{len(kept) + len(rejected)} kept")

    print(f"Kept {total_kept} chunks -> {FILTERED_CHUNKS_PATH}")
    print(f"Rejected {total_rejected} chunks -> {REJECTED_CHUNKS_PATH}")


if __name__ == "__main__":
    main()
