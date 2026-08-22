import csv
import sys
from pathlib import Path
from string import Template

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
from evaluate_spo_extraction import TEST_SET_PATH, evaluate_extractor

RAW_PATH = BASE_DIR / "output/evals/llm_raw/spo_gpt_raw.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/spo_extraction_llm_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/spo_extraction_llm_predictions.csv"

MODEL = "openai/gpt-4.1-mini"
MODEL_LABEL = "GPT-4.1-mini (zero-shot)"

CSV_FIELDS = ["item_id", "sentence", "subject_text", "predicate", "object_text"]

PROMPT = Template("""
Bạn là chuyên gia xử lý ngôn ngữ tự nhiên tiếng Việt, chuyên trích xuất quan hệ nhân quả subject-predicate-object từ câu.

## Bối cảnh

Mỗi câu đầu vào đã là một câu đơn (đã được tách sẵn từ câu phức), diễn đạt tối đa MỘT quan hệ nhân quả. Với mỗi câu, xác định câu có thể hiện quan hệ nhân quả (một vế làm phát sinh, thúc đẩy, hỗ trợ, cản trở hoặc làm thay đổi trạng thái của vế còn lại) hay không, và nếu có, trích ra ba thành phần.

## NHIỆM VỤ

Với mỗi câu:

1. Nếu câu KHÔNG thể hiện quan hệ nhân quả nào, trả về `subject_text`, `predicate`, `object_text` đều là `null`.
2. Nếu câu thể hiện đúng một quan hệ nhân quả, trích trực tiếp trên câu gốc (KHÔNG viết lại):
   * **subject_text** — vế nguyên nhân/yếu tố tác động.
   * **predicate** — từ/cụm từ nối biểu thị quan hệ tác động, hoặc `null` nếu quan hệ ngầm định không có từ nối tường minh (ví dụ "Thiếu vốn, năng suất giảm." → predicate: null).
   * **object_text** — vế kết quả/yếu tố bị tác động.

`subject_text`, `predicate`, `object_text` PHẢI là span xuất hiện nguyên văn trong câu gốc, giữ đúng thứ tự xuất hiện — không diễn giải, không chuẩn hóa, không rút gọn. Nếu câu vẫn thể hiện nhiều hơn một quan hệ, chỉ giữ lại quan hệ rõ ràng/chính nhất.

## GIỮ ĐỦ SPAN

Không rút subject_text/object_text quá ngắn nếu làm mất nghĩa của quan hệ: giữ nguyên phủ định ("không tăng" không đổi thành "giảm"), mức độ, số lượng, và chủ thể của mệnh đề kết quả. Ví dụ trong câu "Công nghệ giúp nông dân giảm chi phí", object_text phải là "nông dân giảm chi phí" (giữ chủ thể "nông dân"), không phải chỉ "giảm chi phí".

## KHÔNG tính là quan hệ nhân quả nếu chỉ mang tính

* phát ngôn/nhận định ("cho biết", "nhận định", "cho rằng", "nhấn mạnh"...);
* xác định/thông báo ("xác định", "nêu", "khẳng định");
* sở hữu/thuộc tính ("là", "có", "thuộc", "gồm");
* mô tả ("được tổ chức bởi", "đến từ", "gắn với" khi chỉ nêu chủ đề/phạm vi);
* tương quan/song song ("đi kèm với", "liên quan đến", "song song với");
* trình tự thời gian đơn thuần ("sau đó", "tiếp theo", "rồi");
* câu phủ định chính quan hệ nhân quả, hoặc chỉ nêu khả năng chưa xác định (ví dụ "Công nghệ số không làm tăng năng suất." → không tách; "Không loại trừ khả năng công nghệ làm tăng chi phí." → không tách).

Nếu quan hệ nhân quả thật sự nằm bên trong một mệnh đề được phát biểu/nhận định, chỉ trích quan hệ nhân quả đó, bỏ phần chủ thể phát ngôn (ví dụ "Ông A cho rằng công nghệ giúp nông dân giảm chi phí." → subject_text: "công nghệ", predicate: "giúp", object_text: "nông dân giảm chi phí").

Không dùng đại từ mơ hồ ("điều này", "nó", "việc đó"...) làm subject_text/object_text nếu tiền ngữ không nằm trong chính câu đang xét — không xác định được thì không tách quan hệ đó (trả về `null` cho cả ba trường).

## ĐẦU VÀO

Mỗi phần tử là một câu cần xử lý.

$sentences

## ĐỊNH DẠNG ĐẦU RA

Chỉ trả về một mảng JSON hợp lệ theo đúng thứ tự câu đầu vào, không giải thích, không thêm Markdown, không đặt trong khối mã:

[
  {
    "sentence": "...",
    "subject_text": "..." hoặc null,
    "predicate": "..." hoặc null,
    "object_text": "..." hoặc null
  }
]
""")

_QUOTE_NORMALIZE = str.maketrans({
    "“": '"', "”": '"',
    "‘": "'", "’": "'",
})


def _normalize_for_compare(text: str) -> str:
    """Model hay tự chuẩn hóa ngoặc kép/nháy cong thành thẳng khi echo lại câu —
    không phải dấu hiệu lệch item, nên bỏ qua khác biệt này khi so khớp."""
    return text.translate(_QUOTE_NORMALIZE).strip()


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict],
) -> list[dict]:
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
            "subject_text": parsed.get("subject_text") or "",
            "predicate": parsed.get("predicate") or "",
            "object_text": parsed.get("object_text") or "",
        })
    return rows


def load_raw(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["item_id"]: row for row in csv.DictReader(f)}


def fetch_predictions(items: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Gọi API cho các câu chưa có trong raw CSV — chạy lại script chỉ tốn phí
    cho phần còn thiếu (lỗi batch, bị ngắt giữa chừng), không gọi lại toàn bộ."""
    done = load_raw(RAW_PATH)
    remaining = [item for item in items if item["item_id"] not in done]

    if remaining:
        print(f"{len(done)} câu đã có sẵn, gọi API cho {len(remaining)} câu còn lại (model={MODEL}).")
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
        print(f"Đã có sẵn dự đoán cho toàn bộ {len(items)} câu, không gọi API.")

    return done


def main():
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").fillna("").reset_index(drop=True)
    items = [
        {"item_id": str(i), "sentence": sentence}
        for i, sentence in enumerate(df["simple_sentence"])
    ]

    predictions_by_id = fetch_predictions(items)

    n_missing = len(df) - len(predictions_by_id)
    if n_missing:
        print(
            f"CẢNH BÁO: thiếu dự đoán cho {n_missing}/{len(df)} câu (batch lỗi sau khi đã thử lại). "
            "Các câu này được tính là dự đoán rỗng. Chạy lại script để lấy nốt trước khi dùng "
            "số liệu này đối chiếu với PhoBERT/rule-based trên cùng 361 câu."
        )

    ordered_predictions = []
    for i in range(len(df)):
        pred = predictions_by_id.get(str(i))
        ordered_predictions.append({
            "subject": pred["subject_text"] if pred else "",
            "predicate": pred["predicate"] if pred else "",
            "object": pred["object_text"] if pred else "",
        })

    prediction_iter = iter(ordered_predictions)

    def llm_extractor(_sentence: str) -> dict[str, str]:
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
