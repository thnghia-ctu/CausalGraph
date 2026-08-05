import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR
from src.causal_detection.causal_sentence_runner import CausalSentenceRunner
from src.chunking.chunk_runner import load_chunks


def main():
    output_path = BASE_DIR / "data"
    chunks = load_chunks(output_path)

    rows = CausalSentenceRunner().build_causal_sentences(chunks, output_path=output_path)
    print(f"Total {len(rows)} sentences -> {output_path / 'causal_sentences/causal_sentences.csv'}")


if __name__ == "__main__":
    main()
