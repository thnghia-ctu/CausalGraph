from string import Template
from typing import Any

PROMPT = Template("""
Bạn là một chuyên gia xử lý ngôn ngữ tiếng Việt.

## Nhiệm vụ

Với mỗi câu trong danh sách đầu vào, thực hiện các bước sau:

### 1. Tách câu phức thành câu đơn

* Tách câu có nhiều hành động, kết quả hoặc quan hệ thành nhiều câu đơn.

* Mỗi câu đơn chỉ biểu diễn một quan hệ:

  Subject --Predicate--> Object

* Phải bảo toàn toàn bộ ý nghĩa của câu gốc.

* Không được thêm thông tin không có trong câu gốc.

* Không được làm mất các thông tin về số lượng, tỷ lệ, mức độ hoặc đối tượng.

* Khi câu có các dấu hiệu như “từ đó”, “do đó”, “nhờ vậy”, phải giữ đúng quan hệ giữa kết quả trước và hệ quả sau.

* Không được biến hệ quả gián tiếp thành tác động trực tiếp.

### 2. Trích xuất cấu trúc S-P-O

Với mỗi câu đơn, xác định `subject`, `predicate`, `object`.

`subject.text` và `object.text` phải là các cụm từ xuất hiện nguyên văn trong câu đơn (hoặc cách diễn đạt tối thiểu cần thiết để bảo toàn tham chiếu của câu gốc).

### 3. Phân tích concept_candidate và state

Từ `subject.text` và `object.text`, xác định:

* `concept_candidate`: thực thể, hiện tượng hoặc khái niệm chính, phải là một cụm con nằm trong `text` tương ứng.
* `state`: trạng thái, xu hướng, mức độ, số lượng hoặc thuộc tính đang được mô tả cho concept_candidate.

Ví dụ:

* `text`: `"giảm công_sức lao_động"`
  → `concept_candidate`: `"công_sức lao_động"`
  → `state`: `"giảm"`

* `text`: `"tăng năng_suất 30%"`
  → `concept_candidate`: `"năng_suất"`
  → `state`: `"tăng 30%"`

* `text`: `"những ứng_dụng này"`
  → `concept_candidate`: `"ứng_dụng"`
  → `state`: `null`

Nếu không xác định được state, trả về `null`.

Giữ nguyên phủ định trong `state`, không suy diễn thành chiều ngược lại (vd: `"không tăng"` phải giữ nguyên là `"không tăng"`, không được đổi thành `"giảm"`).

## Đầu vào

$sentences

## Định dạng đầu ra

Chỉ trả về một mảng JSON hợp lệ theo đúng schema sau:

[
  {
    "original_sentence": "...",
    "simple_sentences": [
      {
        "sentence": "...",
        "subject": {
          "text": "...",
          "concept_candidate": "...",
          "state": null
        },
        "predicate": "...",
        "object": {
          "text": "...",
          "concept_candidate": "...",
          "state": "..."
        }
      }
    ]
  }
]

## Quy tắc bắt buộc

* Mỗi phần tử đầu ra tương ứng với đúng một câu đầu vào.
* Giữ nguyên thứ tự các câu đầu vào.
* `original_sentence` phải giữ nguyên nội dung câu đầu vào.
* `simple_sentences` luôn là một mảng.
* Luôn có đầy đủ tất cả các field trong schema.
* Dùng JSON `null` khi giá trị không tồn tại hoặc không xác định được.
* Không dùng chuỗi `"None"`, `"null"` hoặc chuỗi rỗng để thay cho `null`.
* Không giải thích kết quả.
* Không thêm nhận xét.
* Không thêm Markdown.
* Không đặt JSON trong khối mã.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.

""")

CSV_FIELDS = [
    "doc_id",
    "url",
    "original_sentence",
    "simple_sentence",
    "subject_text",
    "source_concept_candidate",
    "source_state",
    "predicate",
    "object_text",
    "target_concept_candidate",
    "target_state",
]


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item, parsed in zip(batch, result):
        for simple in parsed["simple_sentences"]:
            subject = simple["subject"]
            object_ = simple["object"]
            rows.append(
                {
                    "doc_id": item["doc_id"],
                    "url": item["url"],
                    "original_sentence": parsed["original_sentence"],
                    "simple_sentence": simple["sentence"],
                    "subject_text": subject["text"],
                    "source_concept_candidate": subject["concept_candidate"],
                    "source_state": subject["state"],
                    "predicate": simple["predicate"],
                    "object_text": object_["text"],
                    "target_concept_candidate": object_["concept_candidate"],
                    "target_state": object_["state"],
                }
            )

    return rows
