import json
import re
from string import Template
from typing import Any

PROMPT = Template("""
Bạn nhận một câu gốc và các quan hệ Subject-Predicate-Object đã được trích sẵn từ câu đó.

Nhiệm vụ DUY NHẤT của bạn là biểu diễn MỖI quan hệ thành đúng MỘT câu đơn tiếng Việt — đây là nhiệm vụ GHÉP CÂU từ các cụm đã có, KHÔNG phải nhiệm vụ trích xuất lại hay diễn giải câu gốc.

## NGUYÊN TẮC CỐT LÕI — ưu tiên tuyệt đối việc bảo toàn 3 cụm đã cho hơn việc làm câu văn tự nhiên

1. Phải giữ nguyên tuyệt đối, nguyên văn: subject_text, predicate (nếu khác null), object_text.
2. Không được: sửa chính tả, thay từ, diễn giải lại, rút gọn, mở rộng, thêm thông tin, thêm quan hệ, đổi phủ định, đổi chiều quan hệ.
3. Không được tự thêm bất kỳ từ nào mang thời/thể/tình thái/mức độ/phủ định nếu từ đó không có sẵn trong 3 cụm đã cho — ví dụ tuyệt đối không tự thêm "đã", "sẽ", "có thể", "không", "rất", "do đó", "vì vậy", "khiến", "gây ra".
4. Chỉ được thêm dấu câu và từ chức năng tối thiểu cần thiết để nối 3 cụm thành câu (vd "là", dấu phẩy, dấu chấm cuối câu).
5. Nếu predicate là null: chỉ nối subject_text và object_text bằng dấu câu tối thiểu (thường là dấu phẩy) theo đúng quan hệ nhân quả ngầm định đã có sẵn trong câu gốc — KHÔNG tự thêm động từ/từ nối nào để biểu thị quan hệ đó.
6. PHẢI đọc lại `sentence` (câu gốc đầy đủ) để xác định đúng thứ tự thật ba cụm xuất hiện trong đó, rồi viết câu đơn theo đúng thứ tự thật đó — thứ tự liệt kê subject_text/predicate/object_text trong `relations` chỉ để tham khảo, không phải thứ tự bắt buộc phải viết. Không mặc định rập khuôn "chủ ngữ - vị ngữ - tân ngữ". Chỉ khi giữ đúng thứ tự thật khiến câu không thể chấp nhận được về ngữ pháp, mới được điều chỉnh tối thiểu — nhưng vẫn phải giữ nguyên văn cả 3 cụm.
7. Có thể có nhiều cách biểu diễn hợp lệ, không cần ép về một cấu trúc câu duy nhất — miễn tuân thủ đầy đủ các nguyên tắc trên.

Đặc biệt khi predicate là từ nối đứng ĐẦU câu gốc (kiểu "Nhờ X, Y...", "Do X nên Y...", "Để X, Y..."), câu đơn cũng phải đặt predicate lên đầu, không đẩy xuống giữa câu.

Ví dụ:

Câu gốc: "Nhờ ứng dụng công nghệ số, hoạt động sản xuất kinh doanh của HTX Yến Dương đã đạt nhiều kết quả tích cực."
subject_text: "ứng dụng công nghệ số" | predicate: "Nhờ" | object_text: "hoạt động sản xuất kinh doanh của HTX Yến Dương đã đạt nhiều kết quả tích cực"

SAI (đảo thành chủ ngữ-vị ngữ-tân ngữ, sai thứ tự thật trong câu gốc):
"ứng dụng công nghệ số Nhờ hoạt động sản xuất kinh doanh của HTX Yến Dương đã đạt nhiều kết quả tích cực."

ĐÚNG (giữ đúng thứ tự predicate đứng đầu như câu gốc):
"Nhờ ứng dụng công nghệ số, hoạt động sản xuất kinh doanh của HTX Yến Dương đã đạt nhiều kết quả tích cực."

Câu gốc: "Do ảnh hưởng của Covid-19, nhiều doanh nghiệp phá sản và đối mặt với khó khăn."
subject_text: "ảnh hưởng của Covid-19" | predicate: null | object_text: "nhiều doanh nghiệp phá sản"

SAI (tự bịa từ nối biểu thị quan hệ nhân quả không có trong dữ liệu):
"Ảnh hưởng của Covid-19 khiến nhiều doanh nghiệp phá sản."

ĐÚNG (chỉ nối bằng dấu phẩy, không bịa từ):
"Ảnh hưởng của Covid-19, nhiều doanh nghiệp phá sản."

## Đầu vào

Mỗi phần tử gồm câu gốc (`sentence`) và danh sách quan hệ (`relations`) của câu đó.

$sentences

## Định dạng đầu ra

Chỉ trả về một mảng JSON hợp lệ:

[
  {
    "sentence": "...",
    "simple_sentences": ["...", "..."]
  }
]

* Mỗi phần tử output tương ứng chính xác với một câu input, giữ nguyên thứ tự.
* `simple_sentences` có đúng số phần tử bằng số quan hệ (`relations`) của câu đó, giữ nguyên thứ tự quan hệ.
* Không giải thích, không thêm Markdown, không đặt JSON trong code block.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.
""")

CSV_FIELDS = ["item_id", "simple_index", "simple_sentence", "grounded"]


def build_items_prompt_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "sentence": item["sentence"],
        "relations": [
            {
                "subject_text": relation["subject_text"],
                "predicate": relation["predicate"],
                "object_text": relation["object_text"],
            }
            for relation in item["relations"]
        ],
    }


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value or "").strip().casefold()


def is_grounded(simple_sentence: str, subject_text: str, predicate: str | None, object_text: str) -> bool:
    normalized_sentence = _normalize(simple_sentence)
    for span in (subject_text, predicate, object_text):
        if not span:
            continue
        if _normalize(span) not in normalized_sentence:
            return False
    return True


def flatten_batch_result(
    batch: list[dict[str, Any]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item, parsed in zip(batch, result):
        phrased = parsed.get("simple_sentences", [])

        for relation, simple_sentence in zip(item["relations"], phrased):
            simple_sentence = simple_sentence if isinstance(simple_sentence, str) else ""
            grounded = bool(simple_sentence) and is_grounded(
                simple_sentence, relation["subject_text"], relation["predicate"], relation["object_text"]
            )

            rows.append({
                "item_id": item["item_id"],
                "simple_index": relation["simple_index"],
                "simple_sentence": simple_sentence,
                "grounded": grounded,
            })

        for relation in item["relations"][len(phrased):]:
            rows.append({
                "item_id": item["item_id"],
                "simple_index": relation["simple_index"],
                "simple_sentence": "",
                "grounded": False,
            })

    return rows
