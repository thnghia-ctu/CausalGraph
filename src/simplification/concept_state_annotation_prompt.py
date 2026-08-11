import re
from string import Template
from typing import Any

PROMPT = Template("""
Bạn trích xuất concept_candidate và state từ các cụm từ ngắn (factor) đã cho.

## Bối cảnh

Mỗi factor là một cụm từ đã được trích sẵn, đóng vai trò subject hoặc object trong một quan hệ nhân quả — KHÔNG phải cả câu.

## Nhiệm vụ

Với MỖI factor, xác định:

* `concept_candidate`: thực thể/khái niệm chính đang được nói tới trong factor.
* `state`: trạng thái, xu hướng, mức độ, số lượng hoặc thuộc tính đang mô tả concept_candidate — `null` nếu factor không thể hiện trạng thái nào.

## NGUYÊN TẮC CỐT LÕI — ưu tiên tuyệt đối việc bảo toàn nguyên văn hơn việc diễn đạt tự nhiên

1. `concept_candidate` và `state` (nếu khác null) PHẢI là cụm từ COPY NGUYÊN VĂN, LIÊN TỤC (không được nhảy cóc bỏ qua từ ở giữa), xuất hiện trong chính factor đang xét — không đổi từ, không viết lại, không rút gọn, không suy diễn, không thêm từ không có trong factor. Nếu phần số liệu/tỷ lệ không nằm liền kề với từ chỉ xu hướng (vd factor viết "tăng năng suất 30%" — "tăng" và "30%" không liền nhau), chỉ lấy phần liên tục chứa từ chỉ xu hướng làm `state`, bỏ phần số liệu tách rời — không được ghép 2 đoạn rời rạc thành một `state`.
2. `concept_candidate` và `state` KHÔNG được chồng lấn — không được cùng chứa một từ.
3. Giữ nguyên phủ định trong `state` — không suy diễn thành chiều ngược lại.
4. Nếu factor không thể hiện trạng thái nào (chỉ là tên một thực thể/khái niệm trung lập), `state` phải là `null` — không tự bịa một trạng thái không có trong factor.
5. Nếu không tách được `concept_candidate` hợp lý (factor chỉ là đại từ mơ hồ, không rõ nghĩa), vẫn trả về `concept_candidate` là toàn bộ factor, `state: null` — không được bỏ trống hay bịa nội dung khác.

## Ví dụ

Factor: "giảm công sức lao động"
→ concept_candidate: "công sức lao động" | state: "giảm"

Factor: "năng suất tăng 30%"
→ concept_candidate: "năng suất" | state: "tăng 30%"

Factor: "tăng năng suất 30% so với năm ngoái"
→ concept_candidate: "năng suất" | state: "tăng" (không lấy "30%" vì không liền kề với "tăng")

Factor: "những ứng dụng này"
→ concept_candidate: "ứng dụng" | state: null

Factor: "không tăng năng suất"

SAI (đảo phủ định thành chiều ngược, không có trong factor):
state: "giảm"

ĐÚNG (giữ nguyên phủ định):
state: "không tăng"

## Đầu vào

Mỗi phần tử là một factor cần xử lý.

$sentences

## Định dạng đầu ra

Chỉ trả về một mảng JSON hợp lệ, đúng thứ tự, đúng số lượng với đầu vào:

[
  {
    "factor": "...",
    "concept_candidate": "...",
    "state": null
  }
]

* `factor` phải giữ nguyên 100% nội dung factor đầu vào tương ứng.
* `state` là JSON `null` (không phải chuỗi `"null"` hay chuỗi rỗng) khi không xác định được.
* Không giải thích, không thêm Markdown, không đặt JSON trong code block.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.
""")

CSV_FIELDS = ["item_id", "concept_candidate", "state", "grounded"]


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value or "").strip().casefold()


def _find_span(haystack: str, needle: str) -> tuple[int, int] | None:
    if not needle:
        return None
    idx = haystack.find(needle)
    if idx == -1:
        return None
    return idx, idx + len(needle)


def is_grounded(factor_text: str, concept_candidate: str | None, state: str | None) -> bool:
    haystack = _normalize(factor_text)

    if not concept_candidate:
        return False
    concept_span = _find_span(haystack, _normalize(concept_candidate))
    if concept_span is None:
        return False

    if not state:
        return True
    state_span = _find_span(haystack, _normalize(state))
    if state_span is None:
        return False

    c_start, c_end = concept_span
    s_start, s_end = state_span
    return c_end <= s_start or s_end <= c_start


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item, parsed in zip(batch, result):
        echoed_factor = parsed.get("factor")
        aligned = isinstance(echoed_factor, str) and _normalize(echoed_factor) == _normalize(item["sentence"])

        concept_candidate = parsed.get("concept_candidate")
        state = parsed.get("state")
        grounded = aligned and isinstance(concept_candidate, str) and is_grounded(
            item["sentence"], concept_candidate, state if isinstance(state, str) else None
        )

        rows.append({
            "item_id": item["item_id"],
            "concept_candidate": concept_candidate if grounded else "",
            "state": (state if grounded and isinstance(state, str) else "") or "",
            "grounded": grounded,
        })

    for item in batch[len(result):]:
        rows.append({
            "item_id": item["item_id"],
            "concept_candidate": "",
            "state": "",
            "grounded": False,
        })

    return rows


def concept_state_agree(rows_by_model: dict[str, list[dict[str, Any]]]) -> bool:
    if any(len(rows) != 1 for rows in rows_by_model.values()):
        return False
    if any(not rows[0]["grounded"] for rows in rows_by_model.values()):
        return False

    signatures = {
        (_normalize(rows[0]["concept_candidate"]), _normalize(rows[0]["state"]))
        for rows in rows_by_model.values()
    }
    return len(signatures) == 1
