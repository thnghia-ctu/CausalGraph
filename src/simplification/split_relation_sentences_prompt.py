import json
import re
from string import Template
from typing import Any

PROMPT = Template("""
Bạn là chuyên gia xử lý ngôn ngữ tự nhiên tiếng Việt, chuyên trích xuất quan hệ nhân quả từ câu phức và dựng câu đơn tương ứng cho từng quan hệ.

## Bối cảnh

Các câu đầu vào được trích từ bài báo về chuyển đổi số nông nghiệp. Mỗi câu đã được một bộ phân loại theo từ khóa (trigger-based) gắn nhãn "có khả năng nhân quả", dựa trên một từ/cụm từ tín hiệu (`trigger`) xuất hiện trong câu. **Trigger chỉ là gợi ý, không phải sự xác nhận** — nhiều câu đi qua bộ lọc này không thực sự chứa quan hệ nhân quả.

## NHIỆM VỤ

Với mỗi câu, hãy:

1. Xác định tất cả quan hệ nhân quả **hợp lệ** mà câu thực sự thể hiện — bao gồm cả quan hệ có từ nối tường minh và quan hệ ngầm định rõ ràng (xem mục "QUAN HỆ NGẦM ĐỊNH"). Có thể có 0, 1, hoặc nhiều quan hệ.
2. Với MỖI quan hệ, định vị trực tiếp trên **câu gốc** (`sentence`, KHÔNG phải một câu bạn tự viết ra) ba thành phần:
   * **subject_text** (S) — vế nguyên nhân/yếu tố tác động.
   * **predicate** (R) — từ/cụm từ nối biểu thị quan hệ tác động, hoặc `null` nếu quan hệ ngầm định không có từ nối tường minh.
   * **object_text** (T) — vế kết quả/yếu tố bị tác động.

   S, predicate, object_text PHẢI là span xuất hiện nguyên văn trong câu gốc (trừ ngoại lệ tỉnh lược ở mục dưới). S và T có thể là danh từ, cụm danh từ, cụm động từ, cụm tính từ, hoặc **cả một mệnh đề** — miễn là đó là đơn vị cần thiết để giữ nguyên nghĩa quan hệ (xem mục "GIỮ ĐỦ SPAN"). Bạn KHÔNG cần dựng câu đơn hoàn chỉnh — hệ thống sẽ tự ghép từ ba span này.

Kết quả sẽ dùng làm dữ liệu huấn luyện cho hai mô hình: một mô hình tách câu (học cặp câu gốc – câu đơn) và một mô hình gán nhãn subject/predicate/object trên câu đơn. Vì vậy mọi giá trị PHẢI trung thực tuyệt đối với câu gốc.

## NGUYÊN TẮC QUAN TRỌNG NHẤT: ĐÂY LÀ TRÍCH XUẤT, KHÔNG PHẢI VIẾT LẠI

`subject_text`, `predicate`, `object_text` PHẢI là các span xuất hiện nguyên văn trong **câu gốc**, giữ đúng thứ tự xuất hiện — không diễn giải, không chuẩn hóa, không rút gọn thành một khái niệm ngắn hơn.

KHÔNG được:

* diễn giải lại bằng từ khác, chuẩn hóa cách hành văn;
* thêm từ nối, thêm chủ ngữ, thêm thông tin không có trong câu gốc;
* rút ngắn subject_text/object_text làm mất trạng thái, mức độ, số lượng hoặc phủ định;
* gộp hai quan hệ độc lập thành một;
* tự bịa `predicate` nếu câu không có từ nối tường minh — trong trường hợp đó `predicate` phải là `null`.

### Ngoại lệ duy nhất: khôi phục thành phần bị tỉnh lược trong cấu trúc liệt kê

Khi câu gốc dùng chung một chủ ngữ hoặc một động từ cho nhiều kết quả liệt kê, `subject_text`/`predicate`/`object_text` của một quan hệ được phép **lặp lại đúng nguyên văn** thành phần bị tỉnh lược đó để tự đủ nghĩa — không được thêm bất kỳ từ nào khác ngoài từ đã tỉnh lược.

**TUYỆT ĐỐI KHÔNG được làm ngược lại**: gộp nhiều kết quả liệt kê thành MỘT `object_text` duy nhất nối bằng dấu phẩy, dù chúng dùng chung subject_text/predicate. Mỗi kết quả liệt kê PHẢI là một quan hệ (một phần tử trong mảng `relations`) riêng biệt — kể cả khi điều đó khiến subject_text/predicate bị lặp lại giống hệt nhau giữa các quan hệ.

Ví dụ:

Câu gốc: "Robot đặt hạt rau củ, quả tự động, máy sấy lạnh tăng tốc có thể giúp người làm nông nghiệp tăng năng suất, chất lượng sản phẩm."

ĐÚNG — hai quan hệ:

* subject_text: "Robot đặt hạt rau củ, quả tự động, máy sấy lạnh tăng tốc"
  predicate: "có thể giúp"
  object_text: "người làm nông nghiệp tăng năng suất"

* subject_text: "Robot đặt hạt rau củ, quả tự động, máy sấy lạnh tăng tốc"
  predicate: "có thể giúp"
  object_text: "người làm nông nghiệp tăng chất lượng sản phẩm"

("tăng" được lặp lại trong object_text vì nó bị tỉnh lược ở vế sau trong câu gốc — đây là từ duy nhất được phép thêm, không phải từ mới.)

SAI — gộp thành một quan hệ duy nhất, object_text nối 2 kết quả bằng dấu phẩy:

* subject_text: "Robot đặt hạt rau củ, quả tự động, máy sấy lạnh tăng tốc"
  predicate: "có thể giúp"
  object_text: "người làm nông nghiệp tăng năng suất, chất lượng sản phẩm"

  ← SAI. Phải tách thành 2 quan hệ như ở phần ĐÚNG bên trên, không được gộp lại chỉ vì tiện.

## GIỮ ĐỦ SPAN CHO SUBJECT_TEXT VÀ OBJECT_TEXT

Không rút subject_text/object_text quá ngắn nếu việc rút ngắn làm mất nghĩa của quan hệ. Nếu vế đó biểu thị một trạng thái thay đổi (tăng/giảm/mức độ/số lượng/phủ định) hoặc một mệnh đề có chủ ngữ riêng, giữ nguyên toàn bộ trạng thái/mệnh đề đó trong span — không tách bỏ chủ thể của mệnh đề kết quả.

Ví dụ: "nông dân giảm chi phí" không được rút thành "chi phí"; "tăng năng suất 30%" không được rút thành "năng suất"; "không thể sản xuất" không được rút thành "sản xuất". Trong câu "Công nghệ giúp nông dân giảm chi phí", object_text phải là "nông dân giảm chi phí" (giữ chủ thể "nông dân"), không phải chỉ "giảm chi phí".

## VAI TRÒ CỦA TRIGGER

Mỗi câu đầu vào đi kèm `trigger` — từ/cụm từ đã khiến câu này được gắn nhãn nhân quả. Trigger là điểm khởi đầu để bạn tìm quan hệ, KHÔNG giới hạn phạm vi tìm kiếm: nếu câu còn chứa quan hệ nhân quả khác không liên quan tới trigger, vẫn tách ra bình thường.

Ngược lại, nếu sau khi áp dụng đầy đủ các quy tắc bên dưới mà **không có quan hệ nhân quả tường minh nào trong câu** — kể cả xoay quanh chính trigger đã cho — trả về danh sách quan hệ rỗng cho câu đó. Đây là trường hợp trigger bắt nhầm (false positive), rất phổ biến, đừng cố ép ra một quan hệ chỉ vì trigger có mặt.

Ví dụ:

Câu: "Trung tâm Khuyến nông Quốc gia phối hợp với Sở NN-PTNT Hậu Giang tổ chức diễn đàn Khuyến nông @ Nông nghiệp gắn với truy xuất nguồn gốc."
Trigger: "gắn với"

→ relations: [] — "gắn với" ở đây chỉ nêu chủ đề của diễn đàn (quan hệ mô tả/chủ đề), không phải một vế tác động gây ra vế kia. Không có subject/object nào đóng vai trò nguyên nhân-kết quả trong câu này.

## THẾ NÀO LÀ MỘT QUAN HỆ NHÂN QUẢ HỢP LỆ

Chỉ tách một quan hệ khi câu thực sự thể hiện tác động một chiều: một vế làm phát sinh, thúc đẩy, hỗ trợ, cản trở hoặc làm thay đổi trạng thái của vế còn lại.

Tín hiệu thường gặp (chỉ để tham khảo, KHÔNG bắt buộc, và có mặt trong danh sách này không đồng nghĩa chắc chắn có quan hệ nhân quả): khiến, làm cho, gây ra, dẫn đến, giúp, hỗ trợ, mang lại, tạo ra, thúc đẩy, làm tăng, làm giảm, ảnh hưởng đến, tác động đến, nhờ, do, bởi, vì, nên, kết quả là, mở đường cho.

### KHÔNG tính là quan hệ nhân quả nếu chỉ mang tính:

* phát ngôn/nhận định: "cho biết", "nhận định", "cho rằng", "nhấn mạnh", "theo ông A...";
* xác định/thông báo: "xác định", "nêu", "khẳng định";
* sở hữu/thuộc tính: "là", "có", "thuộc", "gồm";
* mô tả: "được tổ chức bởi", "đến từ", "gắn với" (khi chỉ nêu chủ đề/phạm vi, không phải tác động);
* tương quan/song song: "đi kèm với", "liên quan đến", "song song với";
* trình tự thời gian đơn thuần: "sau đó", "tiếp theo", "rồi";
* chuỗi hành động không hướng tới một trạng thái/kết quả cụ thể.

Nếu quan hệ nhân quả thật sự nằm BÊN TRONG một mệnh đề được phát biểu/nhận định (không phải bản thân hành động phát ngôn), chỉ tách quan hệ nhân quả đó, bỏ phần chủ thể phát ngôn.

Ví dụ: "Ông A cho rằng việc ứng dụng công nghệ giúp nông dân giảm chi phí."
→ subject_text: "việc ứng dụng công nghệ" | predicate: "giúp" | object_text: "nông dân giảm chi phí" (bỏ "Ông A cho rằng")

## MỘT CÂU CÓ THỂ CHO RA NHIỀU QUAN HỆ

Nếu câu chứa nhiều quan hệ nhân quả độc lập, phải tách TẤT CẢ, mỗi quan hệ một object riêng (xem ví dụ Robot ở trên — hai quan hệ độc lập từ một câu).

## QUAN HỆ NHIỀU BƯỚC (A → B → C)

Nếu câu thể hiện chuỗi A → B rồi B → C một cách tường minh, giữ hai quan hệ riêng biệt, KHÔNG gộp thành A → C.

Ví dụ: "A khiến B, từ đó B làm tăng C." → hai quan hệ:
(subject_text="A", predicate="khiến", object_text="B") và (subject_text="B", predicate="làm tăng", object_text="C").

B ở đây có thể là cả một mệnh đề (ví dụ "chi phí sản xuất tăng"), không chỉ một cụm danh từ — object_text của quan hệ 1 và subject_text của quan hệ 2 vẫn phải là cùng một span đó.

## QUAN HỆ NGẦM ĐỊNH (không có từ nối)

Một số câu không có từ nối nhưng vẫn thể hiện quan hệ nhân quả rõ ràng qua trật tự lý do → hệ quả. Vẫn tách quan hệ cho trường hợp này — `predicate` = `null`.

Ví dụ: "Thiếu vốn, năng suất sản xuất giảm."
→ subject_text: "Thiếu vốn" | predicate: null | object_text: "năng suất sản xuất giảm"

Nếu câu có thể đọc hợp lý theo hướng liệt kê, đồng thời, hoặc chỉ trình tự thời gian, KHÔNG tách quan hệ.

## PHỦ ĐỊNH VÀ HEDGING

Giữ nguyên phủ định ("không tăng" không được đổi thành "giảm") và các từ chỉ mức độ chắc chắn ("có thể", "có khả năng") trong subject_text/predicate/object_text.

Nếu câu phủ định chính quan hệ nhân quả, hoặc chỉ nêu khả năng chưa xác định, KHÔNG tách thành quan hệ khẳng định — trả về `relations: []` cho quan hệ đó, không đảo chiều hay suy diễn thành quan hệ khác.

Ví dụ: "Công nghệ số không làm tăng năng suất của nông dân."
→ relations: [] — câu phủ định chính quan hệ nhân quả (không phải "công nghệ làm giảm năng suất", cũng không phải một quan hệ khẳng định nào khác).

Ví dụ: "Không loại trừ khả năng công nghệ số làm tăng chi phí."
→ relations: [] — chỉ nêu khả năng chưa xác định, không khẳng định quan hệ.

## CẤU TRÚC MỤC ĐÍCH ("để", "nhằm", "hướng đến")

Chỉ tách thành quan hệ nhân quả nếu mệnh đề sau biểu thị một kết quả/trạng thái cụ thể.

Ví dụ: "Nông dân lắp cảm biến để giảm chi phí tưới tiêu." → tách (subject_text="Nông dân lắp cảm biến", predicate="để", object_text="giảm chi phí tưới tiêu").
Ví dụ: "Nông dân đến hội thảo để nghe giới thiệu sản phẩm." → KHÔNG tách (chuỗi hành động, không phải trạng thái kết quả).

## MỘT SỐ QUY TẮC NGẮN GỌN KHÁC

* Cấu trúc "do... nên...": `predicate` là một span duy nhất, chọn từ gần vế kết quả nhất (thường "nên"), không gộp cả "do...nên" làm một span.
* Không dùng đại từ mơ hồ ("điều này", "nó", "việc đó"...) làm subject_text/object_text nếu tiền ngữ không nằm trong chính câu đang xét — không xác định được thì KHÔNG tách quan hệ đó.

## KIỂM TRA TRƯỚC KHI TRẢ KẾT QUẢ

Với mỗi quan hệ, tự kiểm tra:

1. subject_text, predicate (nếu khác null), object_text có phải là span nguyên văn trong CÂU GỐC không (trừ đúng từ tỉnh lược được phép lặp lại)?
2. Quan hệ này có chỉ chứa đúng MỘT quan hệ, không gộp hai quan hệ liệt kê, không gộp hai bước của một chuỗi?
3. subject_text/object_text có giữ đủ phủ định/mức độ/số lượng/chủ thể của mệnh đề kết quả không?
4. Tôi có đang nhầm quan hệ phát ngôn, sở hữu, mô tả, tương quan hoặc thời gian thành quan hệ nhân quả không?
5. Nếu câu có nhiều quan hệ, tôi đã tách hết chưa?
6. Nếu trigger là bắt nhầm và câu không có quan hệ nhân quả nào, tôi đã trả về danh sách rỗng chưa, thay vì cố tách một quan hệ gượng ép?

## ĐẦU VÀO

Mỗi phần tử gồm câu cần xử lý (`sentence`) và trigger đã khiến câu này được gắn nhãn nhân quả (`trigger`).

$sentences

## ĐỊNH DẠNG ĐẦU RA

Chỉ trả về một mảng JSON hợp lệ:

[
  {
    "sentence": "...",
    "relations": [
      {
        "subject_text": "...",
        "predicate": "...",
        "object_text": "..."
      }
    ]
  }
]

Nếu câu không chứa quan hệ nhân quả hợp lệ:

[
  {
    "sentence": "...",
    "relations": []
  }
]

## QUY TẮC BẮT BUỘC VỀ OUTPUT

* Mỗi phần tử output tương ứng chính xác với một câu input, giữ nguyên thứ tự.
* `sentence` phải giữ nguyên 100% nội dung câu input.
* `relations` luôn là một mảng (có thể rỗng).
* Mỗi quan hệ gồm đúng ba field: `subject_text`, `predicate`, `object_text`.
* `subject_text`, `predicate` (nếu khác null), `object_text` phải là span nguyên văn trong **câu gốc** (`sentence`).
* `predicate` là JSON `null` (không phải chuỗi `"null"` hay chuỗi rỗng) nếu quan hệ ngầm định không có từ nối tường minh.
* Không tạo quan hệ chỉ vì câu có trigger.
* Không đưa quan hệ phát ngôn, mô tả, sở hữu, tương quan hoặc thời gian vào kết quả.
* Không giải thích ngoài JSON, không thêm Markdown, không đặt JSON trong code block.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.
""")

CSV_FIELDS = [
    "item_id",
    "doc_id",
    "url",
    "chunk_id",
    "sentence_index",
    "trigger",
    "original_sentence",
    "simple_sentence",
    "simple_index",
    "subject_text",
    "predicate",
    "object_text",
]

# simple_index dùng để đánh dấu item không có quan hệ nào (relations rỗng hợp lệ,
# không phải batch lỗi/thiếu output) — xem flatten_batch_result và relations_agree.
NO_RELATION_SENTINEL = -1


def build_simple_sentence(sentence: str, subject_text: str, predicate: str | None, object_text: str) -> str:
    """Ghép cơ học simple_sentence từ 3 span — thay cho việc để LLM tự sinh field
    này. Vị trí thật của S/P/O trong câu gốc không cố định theo một thứ tự nào:
    "S giúp O" (S trước), "O vì S" (O trước, P giữa), "nhờ S, O" (P đứng trước cả
    S lẫn O). Nên sắp cả 3 span theo đúng vị trí ký tự thật trong câu gốc, rồi nối
    lại bằng đúng đoạn văn bản nằm giữa chúng — không giả định thứ tự cố định.

    Một số span (do ngoại lệ tỉnh lược) không phải substring nguyên văn của câu
    gốc — khi đó không tìm được vị trí thật, nối tạm bằng khoảng trắng."""
    spans = [subject_text, object_text]
    if predicate:
        spans.append(predicate)

    not_found = len(sentence) + 1
    positioned = [(sentence.find(text), text) for text in spans]
    positioned = [(pos if pos != -1 else not_found, text) for pos, text in positioned]
    positioned.sort(key=lambda item: item[0])

    parts = [positioned[0][1]]
    for (pos, text), (next_pos, next_text) in zip(positioned, positioned[1:]):
        connector = " "
        if pos != not_found and next_pos != not_found:
            end = pos + len(text)
            if end <= next_pos:
                connector = sentence[end:next_pos] or " "
        parts.append(connector)
        parts.append(next_text)

    return "".join(parts).strip() + "."


def build_prompt(batch: list[dict[str, str]]) -> str:
    sentences_json = json.dumps(
        [{"sentence": item["sentence"], "trigger": item.get("trigger", "")} for item in batch],
        ensure_ascii=False,
        indent=2,
    )

    return PROMPT.substitute(sentences=sentences_json)


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Luôn sinh ít nhất 1 dòng cho mỗi item, kể cả khi relations rỗng (dùng
    simple_index=NO_RELATION_SENTINEL) — để khi ghép ensemble từ nhiều model,
    "model xác nhận câu này không có quan hệ" phân biệt được với "không có dữ
    liệu của model này cho câu này" (batch lỗi/thiếu), thứ chỉ có thể nhận ra
    khi item_id vắng mặt hoàn toàn trên đĩa."""
    rows: list[dict[str, Any]] = []

    for item, parsed in zip(batch, result):
        base = {
            "item_id": item.get("item_id"),
            "doc_id": item["doc_id"],
            "url": item["url"],
            "chunk_id": item.get("chunk_id", ""),
            "sentence_index": item.get("sentence_index", ""),
            "trigger": item.get("trigger", ""),
            "original_sentence": parsed["sentence"],
        }

        relations = [
            r for r in parsed["relations"]
            if isinstance(r.get("subject_text"), str) and isinstance(r.get("object_text"), str)
        ]

        if not relations:
            rows.append({
                **base,
                "simple_sentence": "",
                "simple_index": NO_RELATION_SENTINEL,
                "subject_text": "",
                "predicate": None,
                "object_text": "",
            })
            continue

        for simple_index, relation in enumerate(relations):
            rows.append({
                **base,
                "simple_sentence": build_simple_sentence(
                    parsed["sentence"], relation["subject_text"], relation["predicate"], relation["object_text"]
                ),
                "simple_index": simple_index,
                "subject_text": relation["subject_text"],
                "predicate": relation["predicate"],
                "object_text": relation["object_text"],
            })

    return rows


_EDGE_PUNCT_RE = re.compile(r'^[\s.,;:…"\']+|[\s.,;:…"\']+$')


def _normalize(value: Any) -> str:
    return _EDGE_PUNCT_RE.sub("", value or "")


def relation_signature(row: dict[str, Any]) -> tuple[str, str, str]:
    """Khóa so khớp một quan hệ giữa các model — không quan tâm simple_index
    (thứ tự model liệt kê quan hệ không nhất thiết giống nhau)."""
    return (
        _normalize(row.get("subject_text")),
        _normalize(row.get("predicate")),
        _normalize(row.get("object_text")),
    )


def relations_agree(rows_by_model: dict[str, list[dict[str, Any]]]) -> bool:
    """Đồng thuận khi tập hợp quan hệ (so bằng relation_signature, không quan
    tâm thứ tự) giống hệt nhau giữa TẤT CẢ model — bao gồm cả trường hợp mọi
    model đều đồng ý câu này không có quan hệ nào (mỗi model đúng 1 dòng
    sentinel simple_index=NO_RELATION_SENTINEL)."""
    if not rows_by_model:
        return False

    signature_sets = [
        {relation_signature(row) for row in rows}
        for rows in rows_by_model.values()
    ]

    first = signature_sets[0]
    return all(sig_set == first for sig_set in signature_sets[1:])
