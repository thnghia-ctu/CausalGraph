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

## Cách xử lý danh sách/liệt kê — dễ làm sai nhất, đọc kỹ

* Nếu một câu liệt kê nhiều thực thể/đối tượng cùng đóng vai trò trong **một** hành động/quan hệ duy nhất (subject, predicate hoặc object là một cụm liệt kê, nhưng bản chất vẫn chỉ là MỘT quan hệ), **giữ nguyên cả cụm liệt kê đó trong một câu đơn** — TUYỆT ĐỐI KHÔNG tách theo từng tổ hợp/từng phần tử của danh sách.

  Ví dụ SAI (nổ tổ hợp): câu gốc "Khu thử nghiệm giúp **nông dân, chuyên gia** thử **công nghệ, sáng kiến** mới từ **người nông dân, nhà khoa học** trong và ngoài nước" KHÔNG được tách thành 8-12 câu theo từng tổ hợp chủ thể × đối tượng × nguồn. Đây vẫn là MỘT quan hệ duy nhất (khu thử nghiệm → giúp thử nghiệm), chỉ có các vai trò là cụm liệt kê — giữ nguyên 1 câu đơn, gần như y hệt câu gốc.

* Chỉ tách thành nhiều câu khi câu chứa nhiều HÀNH ĐỘNG/KẾT QUẢ độc lập thật sự — tức là các vế dùng chung chủ ngữ/động từ nhưng mỗi vế là một trạng thái/kết quả riêng biệt đáng kể (thường nhận ra qua nhiều động từ khác nhau, hoặc nhiều kết quả rõ ràng tách bạch về nội dung, không chỉ khác nhau ở một danh từ trong cùng một vai trò).

  Ví dụ ĐÚNG (kết quả liệt kê thật sự): câu gốc "Robot giúp nông dân tăng năng suất, chất lượng sản phẩm" được tách thành 2 câu: "Robot giúp nông dân tăng năng suất." và "Robot giúp nông dân tăng chất lượng sản phẩm." — vì "tăng năng suất" và "tăng chất lượng sản phẩm" là hai kết quả khác nhau, không phải hai giá trị của cùng một vai trò.

* Khi không chắc một danh sách là "nhiều giá trị của cùng một vai trò" (giữ nguyên) hay "nhiều kết quả độc lập" (tách), ưu tiên GIỮ NGUYÊN — tách nhầm (over-split) làm hỏng dữ liệu nặng hơn nhiều so với gộp nhầm.

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


_QUOTE_NORMALIZE = str.maketrans({
    "“": '"', "”": '"',  # “ ”
    "‘": "'", "’": "'",  # ‘ ’
})


def _normalize_for_compare(text: str) -> str:
    """Model hay tự chuẩn hóa ngoặc kép/nháy cong thành thẳng khi echo lại câu —
    không phải dấu hiệu lệch item, nên bỏ qua khác biệt này khi so khớp."""
    return text.translate(_QUOTE_NORMALIZE).strip()


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(result) != len(batch):
        raise ValueError(
            f"Batch có {len(batch)} câu nhưng LLM trả về {len(result)} phần tử — "
            "có khả năng bị lệch item_id nếu cứ ghép theo vị trí."
        )

    rows = []
    for item, parsed in zip(batch, result):
        if _normalize_for_compare(parsed["sentence"]) != _normalize_for_compare(item["sentence"]):
            raise ValueError(
                f"Lệch thứ tự ở item_id={item['item_id']}: gửi {item['sentence']!r}, "
                f"LLM echo lại {parsed['sentence']!r}."
            )
        rows.append({
            "item_id": item["item_id"],
            "sentence": parsed["sentence"],
            "simple_sentences": SENTENCE_SEPARATOR.join(parsed["simple_sentences"]),
        })
    return rows


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
            llm=OpenRouterClient(model=MODELS[model_key], max_tokens=16000),
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
