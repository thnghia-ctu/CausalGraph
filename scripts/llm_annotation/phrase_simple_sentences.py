import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR
from src.llm.batch_processor import BatchProcessor, append_rows_to_csv
from src.llm.openrouter_client import OpenRouterClient
from src.simplification.phrase_simple_sentence_prompt import (
    PROMPT,
    build_items_prompt_payload,
    flatten_batch_result,
)
from src.simplification.split_relation_sentences_prompt import NO_RELATION_SENTINEL

PRIMARY_MODEL = "google/gemini-2.5-flash"

ENSEMBLE_DIR = BASE_DIR / "data" / "ensemble" / "relation_sentences"
ACCEPTED_PATH = ENSEMBLE_DIR / "accepted.csv"
TEST_PREVIEW_PATH = ENSEMBLE_DIR / "phrase_test_preview.csv"
TEST_RAW_PATH = ENSEMBLE_DIR / "phrase_test_raw.csv"
FULL_RAW_PATH = ENSEMBLE_DIR / "phrase_full_raw.csv"
NEEDS_REVIEW_PATH = ENSEMBLE_DIR / "phrase_needs_review.csv"

TEST_SAMPLE_SIZE = 40


class PhraseBatchProcessor(BatchProcessor):
    def build_prompt(self, batch: list[dict[str, Any]]) -> str:
        payload = json.dumps(
            [build_items_prompt_payload(item) for item in batch],
            ensure_ascii=False,
            indent=2,
        )
        return self.prompt.substitute(sentences=payload)


def load_accepted() -> list[dict[str, str]]:
    with ACCEPTED_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_items(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_item: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_item[row["item_id"]].append(row)

    items = []
    for item_id, item_rows in by_item.items():
        relations = [
            {
                "simple_index": row["simple_index"],
                "subject_text": row["subject_text"],
                "predicate": row["predicate"] or None,
                "object_text": row["object_text"],
            }
            for row in item_rows
            if str(row["simple_index"]) != str(NO_RELATION_SENTINEL)
        ]
        if not relations:
            continue
        items.append({
            "item_id": item_id,
            "sentence": item_rows[0]["original_sentence"],
            "relations": relations,
        })
    return items


_GAP_PUNCT_RE = re.compile(r"[,;]")


def has_suspicious_gap(item: dict[str, Any]) -> bool:
    sentence = item["sentence"]
    positions = []
    for relation in item["relations"]:
        for span in (relation["subject_text"], relation["predicate"], relation["object_text"]):
            if not span:
                continue
            pos = sentence.find(span)
            if pos != -1:
                positions.append((pos, pos + len(span)))
    positions.sort()
    for (_, end), (next_pos, _) in zip(positions, positions[1:]):
        if end <= next_pos and _GAP_PUNCT_RE.search(sentence[end:next_pos]):
            return True
    return False


def select_test_sample(items: list[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    suspicious = [item for item in items if has_suspicious_gap(item)]
    suspicious_ids = {item["item_id"] for item in suspicious}
    rest = [item for item in items if item["item_id"] not in suspicious_ids]
    sample = suspicious[:sample_size]
    if len(sample) < sample_size:
        sample += rest[: sample_size - len(sample)]
    return sample


def load_raw(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [
            {**row, "grounded": row["grounded"] == "True"}
            for row in csv.DictReader(f)
        ]


def run(items: list[dict[str, Any]], output_path: Path, resume: bool = False) -> None:
    if resume and output_path.exists():
        done_ids = {row["item_id"] for row in load_raw(output_path)}
        items = [item for item in items if item["item_id"] not in done_ids]
        print(f"Resume: {len(done_ids)} item_id đã có sẵn trong {output_path}, còn {len(items)} cần xử lý.")
    else:
        output_path.unlink(missing_ok=True)

    if not items:
        print("Không còn item nào cần xử lý.")
        return

    processor = PhraseBatchProcessor(
        llm=OpenRouterClient(model=PRIMARY_MODEL),
        items=items,
        prompt=PROMPT,
        flatten_fn=flatten_batch_result,
        fieldnames=["item_id", "simple_index", "simple_sentence", "grounded"],
        output_path=output_path,
    )
    processor.process_batches()


def write_preview(items: list[dict[str, Any]], rows: list[dict[str, Any]], old_by_key: dict[tuple[str, str], str]) -> None:
    preview_rows = []
    sentence_by_item = {item["item_id"]: item["sentence"] for item in items}
    for row in rows:
        key = (row["item_id"], str(row["simple_index"]))
        preview_rows.append({
            "item_id": row["item_id"],
            "original_sentence": sentence_by_item.get(row["item_id"], ""),
            "old_simple_sentence": old_by_key.get(key, ""),
            "new_simple_sentence": row["simple_sentence"],
            "grounded": row["grounded"],
        })
    append_rows_to_csv(
        TEST_PREVIEW_PATH,
        preview_rows,
        fieldnames=["item_id", "original_sentence", "old_simple_sentence", "new_simple_sentence", "grounded"],
    )
    print(f"{len(preview_rows)} câu -> {TEST_PREVIEW_PATH}")
    n_grounded = sum(1 for r in preview_rows if r["grounded"])
    print(f"grounded: {n_grounded}/{len(preview_rows)}")


def update_accepted(rows: list[dict[str, str]], new_rows: list[dict[str, Any]]) -> None:
    rows_by_key = {(row["item_id"], str(row["simple_index"])): row for row in rows}
    new_by_key = {(row["item_id"], str(row["simple_index"])): row for row in new_rows}

    updated = 0
    review_rows = []
    for key, new_row in new_by_key.items():
        row = rows_by_key.get(key)
        if row is None:
            continue
        if new_row["grounded"]:
            row["simple_sentence"] = new_row["simple_sentence"]
            updated += 1
        else:
            row["simple_sentence"] = ""
            review_rows.append({
                "item_id": row["item_id"],
                "simple_index": row["simple_index"],
                "original_sentence": row["original_sentence"],
                "subject_text": row["subject_text"],
                "predicate": row["predicate"],
                "object_text": row["object_text"],
                "llm_attempt": new_row["simple_sentence"],
            })

    with ACCEPTED_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    NEEDS_REVIEW_PATH.unlink(missing_ok=True)
    append_rows_to_csv(
        NEEDS_REVIEW_PATH,
        review_rows,
        fieldnames=["item_id", "simple_index", "original_sentence", "subject_text", "predicate", "object_text", "llm_attempt"],
    )

    still_empty = sum(
        1 for row in rows
        if str(row["simple_index"]) != str(NO_RELATION_SENTINEL) and not row["simple_sentence"]
    )

    print(f"Cập nhật {updated} dòng trong {ACCEPTED_PATH}")
    print(f"grounded: {updated}/{len(new_rows)}, cần review (có ghi lại): {len(review_rows)}/{len(new_rows)} -> {NEEDS_REVIEW_PATH}")
    if still_empty:
        print(
            f"CẢNH BÁO: {still_empty} dòng có quan hệ nhưng vẫn rỗng simple_sentence — "
            f"khả năng cả batch lỗi (không có trong {FULL_RAW_PATH.name}), không nằm trong file review. "
            f"Chạy lại --full sẽ tự resume, chỉ xử lý phần còn thiếu, không tính phí lại phần đã có."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    rows = load_accepted()
    items = build_items(rows)

    if args.full:
        try:
            run(items, FULL_RAW_PATH, resume=True)
        finally:
            new_rows = load_raw(FULL_RAW_PATH)
            update_accepted(rows, new_rows)
        return

    sample = select_test_sample(items, TEST_SAMPLE_SIZE)
    old_by_key = {(row["item_id"], row["simple_index"]): row["simple_sentence"] for row in rows}
    run(sample, TEST_RAW_PATH, resume=False)
    new_rows = load_raw(TEST_RAW_PATH)
    write_preview(sample, new_rows, old_by_key)


if __name__ == "__main__":
    main()
