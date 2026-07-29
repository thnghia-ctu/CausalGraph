import csv
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from underthesea import sent_tokenize

from configs.config import CAUSAL_SENTENCES_PATH, FILTERED_CHUNKS_PATH
from src.causal_detection.trigger_classifier import TriggerCausalClassifier

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


def process_chunk(chunk: dict, classifier: TriggerCausalClassifier) -> list[dict]:
    sentences = sent_tokenize(chunk["text"])

    rows = []
    for sentence_index, sentence in enumerate(sentences):
        triggers = classifier.find_trigger_matches(sentence)
        rows.append({
            "sentence": sentence,
            "weak_label": "causal" if triggers else "non_causal",
            "trigger": triggers[0] if triggers else "",
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "url": chunk["url"],
            "sentence_index": sentence_index,
            "human_label": "",
        })
    return rows


def main():
    classifier = TriggerCausalClassifier()
    chunks = list(iter_chunks(FILTERED_CHUNKS_PATH))

    CAUSAL_SENTENCES_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_sentences = 0
    total_causal = 0

    with open(CAUSAL_SENTENCES_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for chunk_number, chunk in enumerate(chunks, start=1):
            try:
                rows = process_chunk(chunk, classifier)
            except Exception as e:
                print(f"Error processing {chunk['chunk_id']}: {e}")
                traceback.print_exc()
                continue

            writer.writerows(rows)
            f.flush()

            causal_count = sum(1 for row in rows if row["weak_label"] == "causal")
            total_sentences += len(rows)
            total_causal += causal_count
            print(f"[{chunk_number}/{len(chunks)}] {chunk['chunk_id']}: {causal_count}/{len(rows)} causal")

    print(f"Total {total_sentences} sentences, {total_causal} causal -> {CAUSAL_SENTENCES_PATH}")


if __name__ == "__main__":
    main()
