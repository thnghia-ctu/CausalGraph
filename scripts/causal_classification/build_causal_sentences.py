import csv
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from underthesea import sent_tokenize

from configs.config import CAUSAL_SENTENCES_PATH, FILTERED_CHUNKS_PATH

FIELDNAMES = [
    "sentence",
    "weak_label",
    "trigger",
    "chunk_id",
    "doc_id",
    "url",
    "sentence_index",
    "human_label",
]


def iter_chunks(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def process_chunk(chunk: dict) -> list[dict]:
    sentences = sent_tokenize(chunk["text"])

    return [
        {
            "sentence": sentence,
            "weak_label": "",
            "trigger": "",
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "url": chunk["url"],
            "sentence_index": sentence_index,
            "human_label": "",
        }
        for sentence_index, sentence in enumerate(sentences)
    ]


def main():
    chunks = list(iter_chunks(FILTERED_CHUNKS_PATH))

    CAUSAL_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_sentences = 0

    with open(CAUSAL_SENTENCES_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()

        for chunk_number, chunk in enumerate(chunks, start=1):
            try:
                rows = process_chunk(chunk)
            except Exception as e:
                print(f"Error processing {chunk['chunk_id']}: {e}")
                traceback.print_exc()
                continue

            writer.writerows(rows)
            f.flush()

            total_sentences += len(rows)
            print(f"[{chunk_number}/{len(chunks)}] {chunk['chunk_id']}: {len(rows)} sentences")

    print(f"Total {total_sentences} sentences -> {CAUSAL_SENTENCES_PATH}")


if __name__ == "__main__":
    main()
