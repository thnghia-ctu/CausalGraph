import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pandas as pd

from configs.config import BASE_DIR
from src.llm.batch_processor import BatchProcessor
from src.llm.openrouter_client import OpenRouterClient
from src.simplification.concept_state_annotation_prompt import CSV_FIELDS, PROMPT, flatten_batch_result
from evaluate_concept_state_extraction import TEST_SET_PATH, evaluate_extractor

RAW_PATH = BASE_DIR / "output/evals/llm_raw/concept_state_gpt_raw.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_llm_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_llm_predictions.csv"

MODEL = "openai/gpt-4.1-mini"
MODEL_LABEL = "GPT-4.1-mini (zero-shot)"


def load_raw(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["item_id"]: row for row in csv.DictReader(f)}


def fetch_predictions(items: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Gọi API cho các factor chưa có trong raw CSV — chạy lại script chỉ tốn phí
    cho phần còn thiếu (lỗi batch, bị ngắt giữa chừng), không gọi lại toàn bộ."""
    done = load_raw(RAW_PATH)
    remaining = [item for item in items if item["item_id"] not in done]

    if remaining:
        print(f"{len(done)} factor đã có sẵn, gọi API cho {len(remaining)} factor còn lại (model={MODEL}).")
        processor = BatchProcessor(
            llm=OpenRouterClient(model=MODEL),
            items=remaining,
            prompt=PROMPT,
            flatten_fn=flatten_batch_result,
            fieldnames=CSV_FIELDS,
            output_path=RAW_PATH,
        )
        processor.process_batches()
        done = load_raw(RAW_PATH)
    else:
        print(f"Đã có sẵn dự đoán cho toàn bộ {len(items)} factor, không gọi API.")

    return done


def main():
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").fillna("").reset_index(drop=True)
    items = [
        {"item_id": str(i), "sentence": factor_text}
        for i, factor_text in enumerate(df["factor_text"])
    ]

    predictions_by_id = fetch_predictions(items)

    n_missing = len(df) - len(predictions_by_id)
    if n_missing:
        print(
            f"CẢNH BÁO: thiếu dự đoán cho {n_missing}/{len(df)} factor (batch lỗi sau khi đã thử lại). "
            "Các factor này được tính là dự đoán rỗng. Chạy lại script để lấy nốt trước khi dùng "
            "số liệu này đối chiếu với PhoBERT/luật trên cùng 646 factor."
        )

    ordered_predictions = []
    for i in range(len(df)):
        pred = predictions_by_id.get(str(i))
        ordered_predictions.append({
            "concept_candidate": pred["concept_candidate"] if pred else "",
            "state": pred["state"] if pred else "",
        })

    prediction_iter = iter(ordered_predictions)

    def llm_extractor(_factor_text: str) -> dict[str, str]:
        return next(prediction_iter)

    summary, rows = evaluate_extractor(MODEL_LABEL, llm_extractor, df)
    for entry in summary:
        print(entry)

    PREDICTIONS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(PREDICTIONS_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Đã ghi metrics vào {METRICS_OUTPUT_PATH}")
    print(f"Đã ghi dự đoán từng dòng vào {PREDICTIONS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
