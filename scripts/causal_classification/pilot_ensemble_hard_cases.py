import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR
from src.causal_detection.labeling_prompt import CSV_FIELDS, PROMPT, flatten_batch_result
from src.llm.ensemble_runner import EnsembleRunner
from src.llm.openrouter_client import OpenRouterClient

HARD_CASES_PATH = BASE_DIR / "data" / "eval" / "causal_hard_cases.csv"
OUTPUT_DIR = BASE_DIR / "data" / "ensemble" / "causal_pilot"

shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

df = pd.read_csv(HARD_CASES_PATH, sep=";")

items = [
    {"item_id": row.id, "sentence": row.sentence}
    for row in df.itertuples()
]
expected_by_id = {row.id: row for row in df.itertuples()}

runner = EnsembleRunner(
    clients={
        "gemini": OpenRouterClient(model="google/gemini-2.5-flash"),
        "deepseek": OpenRouterClient(model="deepseek/deepseek-v4-flash-0731"),
        "qwen": OpenRouterClient(model="qwen/qwen3.7-flash"),
    },
    items=items,
    prompt=PROMPT,
    flatten_fn=flatten_batch_result,
    fieldnames=CSV_FIELDS,
    agreement_fields=["label"],
    output_dir=OUTPUT_DIR,
    batch_size=10,
    max_workers=5,
)

consensus_rows, disagreement_rows = runner.run()

print("=== Độ khớp từng model so với expected_label ===")
for name in runner.clients:
    grouped = runner.rows_by_model[name]
    correct = 0
    total = 0
    wrong_by_group: dict[str, int] = {}
    for item in items:
        rows = grouped.get(item["item_id"])
        if not rows:
            continue
        total += 1
        expected = expected_by_id[item["item_id"]]
        if rows[0]["label"] == expected.expected_label:
            correct += 1
        else:
            wrong_by_group[expected.group] = wrong_by_group.get(expected.group, 0) + 1

    accuracy = f"{correct}/{total} ({correct / total:.0%})" if total else "không có dữ liệu"
    print(f"{name}: {accuracy}")
    if wrong_by_group:
        print(f"   sai theo nhóm: {wrong_by_group}")

print(f"\n=== Consensus vs Disagreement ===")
print(f"Consensus (3 model khớp nhau): {len(consensus_rows)}/{len(items)}")
print(f"Disagreement (cần review): {len(disagreement_rows)}/{len(items)}")

print("\n=== Chi tiết các ca bất đồng thuận ===")
for row in disagreement_rows:
    expected = expected_by_id.get(row["item_id"])
    if expected is None:
        continue
    labels = {name: row.get(f"{name}_label") for name in runner.clients}
    all_wrong = all(v != expected.expected_label for v in labels.values() if v is not None)
    marker = "  <-- KHÔNG MODEL NÀO ĐÚNG" if all_wrong else ""
    print(f"[{expected.group}] {row['item_id']}: expected={expected.expected_label}, models={labels}{marker}")
