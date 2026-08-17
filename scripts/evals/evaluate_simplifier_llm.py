import argparse
import csv
import sys
from pathlib import Path
from string import Template
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR
from src.llm.batch_processor import BatchProcessor
from src.llm.openrouter_client import OpenRouterClient
from src.simplification.seq2seq_simplifier import SENTENCE_SEPARATOR
from src.simplification.simplifier_eval import score_and_save

TEST_SET_PATH = BASE_DIR / "data/eval/simplification_test.csv"
RAW_DIR = BASE_DIR / "output/evals/llm_raw"
OUTPUT_DIR = BASE_DIR / "output/evals"

MODELS = {
    "gemini": "google/gemini-2.5-flash",
    "kimi": "moonshotai/kimi-k2",
    "gpt": "openai/gpt-4.1-mini",
}

PROMPT = Template("""
Bạn là một chuyên gia xử lý ngôn ngữ tiếng Việt, chuyên tách câu phức thành các câu đơn.

## Nhiệm vụ

Với mỗi câu trong danh sách đầu vào, tách câu thành một hoặc nhiều câu đơn, mỗi câu đơn chỉ diễn đạt một quan hệ/hành động duy nhất (một Subject - Predicate - Object).

## Quy tắc

* Phải bảo toàn toàn bộ ý nghĩa của câu gốc, không thêm thông tin không có trong câu gốc.
* Không được làm mất thông tin về số lượng, tỷ lệ, mức độ hoặc đối tượng.
* Khi câu có các từ nối như "từ đó", "do đó", "nhờ vậy", "khiến", "dẫn đến"..., phải giữ đúng chiều quan hệ giữa nguyên nhân và kết quả khi tách thành các câu đơn.
* Không được biến hệ quả gián tiếp thành tác động trực tiếp.
* Nếu câu gốc đã đơn giản (chỉ một quan hệ), trả về đúng một câu đơn giống câu gốc.

## Đầu vào

$sentences

## Định dạng đầu ra

Chỉ trả về một mảng JSON hợp lệ theo đúng schema sau:

[
  {
    "sentence": "...",
    "simple_sentences": ["...", "..."]
  }
]

## Quy tắc bắt buộc

* Mỗi phần tử đầu ra tương ứng với đúng một câu đầu vào, giữ nguyên thứ tự.
* `sentence` phải giữ nguyên nội dung câu đầu vào.
* `simple_sentences` luôn là một mảng khác rỗng.
* Không giải thích kết quả, không thêm nhận xét, không thêm Markdown.
* Không đặt JSON trong khối mã.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.
""")

CSV_FIELDS = ["item_id", "sentence", "simple_sentences"]


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "item_id": item["item_id"],
            "sentence": parsed["sentence"],
            "simple_sentences": SENTENCE_SEPARATOR.join(parsed["simple_sentences"]),
        }
        for item, parsed in zip(batch, result)
    ]


def load_test_set() -> pd.DataFrame:
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").dropna(subset=["sentence", "simple_sentences"])
    return df[df["simple_sentences"].str.strip() != ""]


def load_raw(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["item_id"]: row["simple_sentences"] for row in csv.DictReader(f)}


def fetch_predictions(model_key: str, items: list[dict[str, str]]) -> dict[str, str]:
    """Gọi API cho các item chưa có trong raw CSV — chạy lại script chỉ tốn phí
    cho phần còn thiếu (lỗi batch, bị ngắt giữa chừng), không gọi lại toàn bộ."""
    raw_path = RAW_DIR / f"{model_key}_raw.csv"
    done = load_raw(raw_path)
    remaining = [item for item in items if item["item_id"] not in done]

    if remaining:
        print(f"{model_key}: {len(done)} câu đã có sẵn, gọi API cho {len(remaining)} câu còn lại.")
        processor = BatchProcessor(
            llm=OpenRouterClient(model=MODELS[model_key]),
            items=remaining,
            prompt=PROMPT,
            flatten_fn=flatten_batch_result,
            fieldnames=CSV_FIELDS,
            output_path=raw_path,
        )
        processor.process_batches()
        done = load_raw(raw_path)
    else:
        print(f"{model_key}: đã có sẵn dự đoán cho toàn bộ {len(items)} câu, không gọi API.")

    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=sorted(MODELS), required=True)
    args = parser.parse_args()

    predictions_output_path = OUTPUT_DIR / f"simplifier_predictions_{args.model}.csv"
    metrics_output_path = OUTPUT_DIR / f"simplifier_metrics_{args.model}.csv"

    df = load_test_set().reset_index(drop=True)
    items = [
        {"item_id": str(i), "sentence": sentence}
        for i, sentence in enumerate(df["sentence"])
    ]

    predictions_by_id = fetch_predictions(args.model, items)

    kept_indices = [i for i in range(len(df)) if str(i) in predictions_by_id]
    n_missing = len(df) - len(kept_indices)
    if n_missing:
        print(f"CẢNH BÁO: thiếu dự đoán cho {n_missing}/{len(df)} câu (batch lỗi) — loại khỏi eval.")

    kept = df.iloc[kept_indices]
    originals = kept["sentence"].tolist()
    gold_simples = [s.split(SENTENCE_SEPARATOR) for s in kept["simple_sentences"].tolist()]
    predicted_simples = [predictions_by_id[str(i)].split(SENTENCE_SEPARATOR) for i in kept_indices]

    score_and_save(originals, gold_simples, predicted_simples, predictions_output_path, metrics_output_path)


if __name__ == "__main__":
    main()
