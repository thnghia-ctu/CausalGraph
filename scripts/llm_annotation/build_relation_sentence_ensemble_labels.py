import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR, CAUSAL_SENTENCES_VERIFIED_PATH
from src.llm.batch_processor import BatchProcessor, append_rows_to_csv
from src.llm.ensemble_runner import EnsembleRunner
from src.llm.openrouter_client import OpenRouterClient
from src.simplification.split_relation_sentences_prompt import (
    CSV_FIELDS,
    NO_RELATION_SENTINEL,
    PROMPT,
    flatten_batch_result,
    relations_agree,
)

PRIMARY_MODEL = "google/gemini-2.5-flash"

OUTPUT_DIR = BASE_DIR / "data" / "ensemble" / "relation_sentences"
ACCEPTED_PATH = OUTPUT_DIR / "accepted.csv"
NEEDS_REVIEW_PATH = OUTPUT_DIR / "needs_review.csv"

ACCEPTED_FIELDS = [*CSV_FIELDS, "source"]
NEEDS_REVIEW_FIELDS = [
    "item_id", "doc_id", "original_sentence", "trigger", "pass",
    "simple_index", "simple_sentence", "subject_text", "predicate", "object_text",
]

AMBIGUOUS_TRIGGER_WORDS = [
    "khiến", "làm cho", "gây ra", "dẫn đến", "giúp", "hỗ trợ", "mang lại",
    "tạo ra", "thúc đẩy", "làm tăng", "làm giảm", "ảnh hưởng đến", "tác động đến",
    "nhờ", "do", "bởi", "vì", "nên", "kết quả là", "mở đường cho",
    "để", "nhằm", "hướng đến",
]
VAGUE_TRIGGERS = {"để", "nhằm", "hướng đến", "gắn với", "liên quan đến", "đi kèm với"}


def is_hard_case(sentence: str, trigger: str) -> bool:
    if not trigger:
        return True
    if trigger in VAGUE_TRIGGERS:
        return True
    if sentence.count(",") >= 2:
        return True
    return sum(sentence.count(w) for w in AMBIGUOUS_TRIGGER_WORDS) >= 2


def build_items() -> list[dict[str, str]]:
    df = pd.read_csv(CAUSAL_SENTENCES_VERIFIED_PATH, encoding="utf-8-sig")
    df["trigger_text"] = df["trigger_text"].fillna("")
    causal_df = df[df["label"] == "causal"].dropna(subset=["sentence"])

    return [
        {
            "item_id": str(index),
            "sentence": row.sentence,
            "trigger": row.trigger_text,
            "doc_id": row.doc_id,
            "url": row.url,
        }
        for index, row in enumerate(causal_df.itertuples())
    ]


def has_relations(rows: list[dict[str, Any]]) -> bool:
    return not (len(rows) == 1 and str(rows[0].get("simple_index")) == str(NO_RELATION_SENTINEL))


def run_easy_pass(items: list[dict[str, str]]) -> None:
    if not items:
        print("Không có câu 'dễ' nào để chạy.")
        return

    processor = BatchProcessor(
        llm=OpenRouterClient(model=PRIMARY_MODEL),
        items=items,
        prompt=PROMPT,
        flatten_fn=flatten_batch_result,
        fieldnames=CSV_FIELDS,
        output_path=OUTPUT_DIR / "easy_raw.csv",
    )
    rows = processor.process_batches()

    by_item = defaultdict(list)
    for row in rows:
        by_item[str(row["item_id"])].append(row)

    accepted_rows = []
    n_no_relation = 0
    for item_rows in by_item.values():
        if has_relations(item_rows):
            accepted_rows.extend({**row, "source": "easy_single_pass"} for row in item_rows)
        else:
            n_no_relation += 1

    append_rows_to_csv(ACCEPTED_PATH, accepted_rows, fieldnames=ACCEPTED_FIELDS)
    print(f"Easy pass: {len(by_item)} câu xử lý, {len(by_item) - n_no_relation} câu có quan hệ, {n_no_relation} câu không có quan hệ (trigger bắt nhầm).")


def load_raw(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not path.exists():
        return grouped
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            grouped[row["item_id"]].append(row)
    return grouped


def build_needs_review_rows(item_id: str, per_pass: dict[str, list[dict[str, Any]]], base: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pass_name, rows in per_pass.items():
        if not rows:
            out.append({
                "item_id": item_id, "doc_id": base.get("doc_id", ""), "original_sentence": base.get("sentence", ""),
                "trigger": base.get("trigger", ""), "pass": pass_name, "simple_index": "",
                "simple_sentence": "(không có output)", "subject_text": "", "predicate": "", "object_text": "",
            })
            continue
        for row in rows:
            out.append({
                "item_id": item_id, "doc_id": row.get("doc_id", ""), "original_sentence": row.get("original_sentence", ""),
                "trigger": row.get("trigger", ""), "pass": pass_name, "simple_index": row.get("simple_index", ""),
                "simple_sentence": row.get("simple_sentence", ""), "subject_text": row.get("subject_text", ""),
                "predicate": row.get("predicate", ""), "object_text": row.get("object_text", ""),
            })
    return out


def run_hard_pass(items: list[dict[str, str]]) -> None:
    if not items:
        print("Không có câu 'khó' nào để chạy.")
        return

    runner = EnsembleRunner(
        clients={
            "pass1": OpenRouterClient(model=PRIMARY_MODEL),
            "pass2": OpenRouterClient(model=PRIMARY_MODEL),
        },
        items=items,
        prompt=PROMPT,
        flatten_fn=flatten_batch_result,
        fieldnames=CSV_FIELDS,
        agreement_fn=relations_agree,
        output_dir=OUTPUT_DIR,
    )
    runner.fetch()

    items_by_id = {item["item_id"]: item for item in items}
    rows_by_pass = {name: load_raw(OUTPUT_DIR / f"{name}_raw.csv") for name in ("pass1", "pass2")}
    processed_item_ids = sorted(
        {item_id for grouped in rows_by_pass.values() for item_id in grouped},
        key=lambda x: int(x) if x.isdigit() else -1,
    )

    accepted_rows = []
    review_rows = []
    n_self_consistent_no_relation = 0
    n_self_consistent_with_relation = 0
    n_needs_review = 0

    for item_id in processed_item_ids:
        item = items_by_id[item_id]
        per_pass = {name: rows_by_pass[name].get(item_id, []) for name in ("pass1", "pass2")}

        if any(len(rows) == 0 for rows in per_pass.values()):
            review_rows.extend(build_needs_review_rows(item_id, per_pass, item))
            n_needs_review += 1
            continue

        if not relations_agree(per_pass):
            review_rows.extend(build_needs_review_rows(item_id, per_pass, item))
            n_needs_review += 1
            continue

        reference = per_pass["pass1"]
        if not has_relations(reference):
            n_self_consistent_no_relation += 1
            continue

        n_self_consistent_with_relation += 1
        accepted_rows.extend({**row, "source": "hard_self_consistent"} for row in reference)

    append_rows_to_csv(ACCEPTED_PATH, accepted_rows, fieldnames=ACCEPTED_FIELDS)
    append_rows_to_csv(NEEDS_REVIEW_PATH, review_rows, fieldnames=NEEDS_REVIEW_FIELDS)

    print(f"Hard pass: {len(processed_item_ids)} câu xử lý, {n_self_consistent_with_relation} câu tự nhất quán có quan hệ, "
          f"{n_self_consistent_no_relation} câu tự nhất quán không có quan hệ, {n_needs_review} câu cần review tay -> {NEEDS_REVIEW_PATH}")


def main() -> None:
    for path in (ACCEPTED_PATH, NEEDS_REVIEW_PATH, OUTPUT_DIR / "easy_raw.csv", OUTPUT_DIR / "pass1_raw.csv", OUTPUT_DIR / "pass2_raw.csv"):
        path.unlink(missing_ok=True)

    items = build_items()
    easy_items = [item for item in items if not is_hard_case(item["sentence"], item["trigger"])]
    hard_items = [item for item in items if is_hard_case(item["sentence"], item["trigger"])]

    print(f"Tổng {len(items)} câu causal -> {len(easy_items)} dễ (1 lần gọi), {len(hard_items)} khó (2 lần gọi, self-consistency).")

    run_easy_pass(easy_items)
    run_hard_pass(hard_items)

    print(f"Dữ liệu chấp nhận -> {ACCEPTED_PATH}")


if __name__ == "__main__":
    main()
