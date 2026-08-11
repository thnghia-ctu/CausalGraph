import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import CAUSAL_SENTENCES_PATH, DATASET_DIR

OUTPUT_PATH = DATASET_DIR / "gold_simplification_candidates.xlsx"
PER_CATEGORY = 40
SEED = 42

GIUP_KHIEN_RE = re.compile(r"\b(giúp|khiến|cho phép|làm cho|làm|nhờ)\b", re.IGNORECASE)
NESTED_RE = re.compile(r"\b(mà còn|trong đó|nhờ đó|qua đó|đồng thời|không chỉ)\b", re.IGNORECASE)
HALLUCINATION_RE = re.compile(r"(\d+([.,]\d+)?\s?%|\d{2,}|[\"“”])")


def word_count(sentence: str) -> int:
    return len(sentence.split())


def comma_count(sentence: str) -> int:
    return sentence.count(",")


DANGLING_TAIL_RE = re.compile(
    r"\s(do|và|của|cho|với|là|trong|theo|nhờ|mà)$"
)


def looks_truncated(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return True
    if not (s[0].isupper() or s[0] in "\"“‘("):
        return True
    if DANGLING_TAIL_RE.search(s.rstrip(".")):
        return True
    return False


def classify(sentence: str) -> list[str]:
    categories = []

    if word_count(sentence) <= 25 and comma_count(sentence) <= 1:
        categories.append("cau_don")

    if comma_count(sentence) >= 2 or sentence.count(" và ") >= 2:
        categories.append("nhieu_dong_tu")

    if GIUP_KHIEN_RE.search(sentence):
        categories.append("giup_khien_cho_phep_lam")

    if NESTED_RE.search(sentence):
        categories.append("chu_ngu_luoc_long_nhau")

    if HALLUCINATION_RE.search(sentence) or word_count(sentence) >= 55:
        categories.append("de_hallucination")

    return categories or ["khac"]


def main():
    df = pd.read_csv(CAUSAL_SENTENCES_PATH, sep=";", encoding="utf-8-sig")
    causal_df = df[df["weak_label"] == "causal"].dropna(subset=["sentence"]).reset_index(drop=True)
    causal_df = causal_df[~causal_df["sentence"].apply(looks_truncated)].reset_index(drop=True)

    causal_df["categories"] = causal_df["sentence"].apply(classify)

    rng = random.Random(SEED)
    picked_idx: set[int] = set()
    rows = []

    for category in ["cau_don", "nhieu_dong_tu", "giup_khien_cho_phep_lam", "chu_ngu_luoc_long_nhau", "de_hallucination"]:
        candidates = [
            i for i in causal_df.index
            if category in causal_df.at[i, "categories"] and i not in picked_idx
        ]
        rng.shuffle(candidates)
        chosen = candidates[:PER_CATEGORY]
        picked_idx.update(chosen)

        for i in chosen:
            row = causal_df.loc[i]
            rows.append({
                "category": category,
                "doc_id": row["doc_id"],
                "url": row["url"],
                "chunk_id": row["chunk_id"],
                "sentence_index": row["sentence_index"],
                "original_sentence": row["sentence"],
                "simple_sentence": "",
                "subject_text": "",
                "predicate": "",
                "object_text": "",
            })

    out_df = pd.DataFrame(rows)
    out_df.to_excel(OUTPUT_PATH, index=False)
    print(f"{len(out_df)} câu -> {OUTPUT_PATH}")
    print(out_df["category"].value_counts())


if __name__ == "__main__":
    main()
