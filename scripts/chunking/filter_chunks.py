import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR
from src.chunking.chunk_runner import ChunkRunner
from src.crawlers.crawl_runner import load_documents


def main():
    output_path = BASE_DIR / "data"
    documents = load_documents(output_path)

    kept = ChunkRunner().chunk_documents(documents, output_path=output_path)
    print(f"Kept {len(kept)} chunks -> {output_path / 'chunks/chunks_filtered.jsonl'}")


if __name__ == "__main__":
    main()
