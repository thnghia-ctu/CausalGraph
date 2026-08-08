from string import Template
from typing import Any

CSV_FIELDS = [
    "item_id",
    "doc_id",
    "url",
    "sentence",
    "label",
    "has_explicit_trigger",
    "trigger_text",
    "reason",
]


def flatten_batch_result(
    batch: list[dict[str, str]],
    result: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item, parsed in zip(batch, result):
        rows.append({
            "item_id": item.get("item_id"),
            "doc_id": item.get("doc_id", ""),
            "url": item.get("url", ""),
            "sentence": parsed["sentence"],
            "label": parsed["label"],
            "has_explicit_trigger": parsed["has_explicit_trigger"],
            "trigger_text": parsed["trigger_text"],
            "reason": parsed["reason"],
        })

    return rows


PROMPT = Template("""
Bạn là chuyên gia xử lý ngôn ngữ tự nhiên tiếng Việt, chuyên về phân tích quan hệ nhân quả trong văn bản.

## Bối cảnh

Các câu này được trích từ bài báo về chuyển đổi số trong nông nghiệp. Nhãn bạn gán sẽ được dùng làm dữ liệu huấn luyện cho một mô hình phân loại câu nhân quả, và câu được gán "causal" sẽ được đưa tiếp vào bước trích xuất bộ ba (yếu tố nguyên nhân, quan hệ, yếu tố kết quả) để dựng đồ thị nhân quả. Vì vậy nhãn "causal" phải phản ánh đúng khả năng trích xuất được một cặp yếu tố cụ thể có quan hệ tác động một chiều, không phải cảm giác chung chung "câu này có nhắc tới nguyên nhân/kết quả".

## Định nghĩa "causal"

Gán `causal` khi câu (hoặc một phần của câu) KHẲNG ĐỊNH rằng một yếu tố/hành động/sự kiện/trạng thái A làm phát sinh, thúc đẩy, cản trở, hoặc làm thay đổi trạng thái của một yếu tố/hành động/sự kiện/trạng thái B khác, theo một chiều tác động xác định (A → B), và cả A lẫn B đều gọi tên được bằng một cụm từ cụ thể xuất hiện trong câu.

A/B có thể là danh từ, cụm danh từ hóa hành động ("việc ứng dụng công nghệ"), hoặc cụm động từ/tính từ chỉ trạng thái ("thiếu vốn", "không thể đầu tư") — miễn là cụ thể. Cái bị loại trừ chỉ là: (a) đại từ mơ hồ như "điều này", "việc đó" KHÔNG có tiền ngữ trong câu, và (b) cụm từ lượng hóa mơ hồ như "nhiều yếu tố", "một số nguyên nhân", "nhiều thay đổi tích cực" không chỉ đích danh được đối tượng nào.

**Có từ nối nhân quả trong câu KHÔNG đồng nghĩa với việc gán `causal`.** Từ nối chỉ là tín hiệu hỗ trợ; quyết định luôn phải dựa trên việc có xác định được một cặp A, B cụ thể hay không.

### Các trường hợp TÍNH LÀ causal

1. **Nhân quả tường minh có từ nối**: do, vì, bởi, khiến, làm cho, gây ra, dẫn đến, nhờ, nên, kết quả là, ảnh hưởng đến, tác động đến...
2. **Mục đích/ý định nêu trạng thái/kết quả cụ thể** (để, nhằm, hướng đến): tính là causal CHỈ KHI mệnh đề mục đích nêu rõ một trạng thái/kết quả có thể thay đổi ở một yếu tố cụ thể (tăng, giảm, cải thiện, tiết kiệm, tránh, hạn chế, đạt được...), dù chưa chắc đã xảy ra trên thực tế. Nếu mệnh đề mục đích chỉ là một hành động/sự kiện tiếp theo, không mang tính trạng thái (vd. "để tham quan mô hình", "để nghe giới thiệu sản phẩm"), gán `non_causal` — không có yếu tố B nào bị tác động, chỉ là chuỗi hành động.
3. **Nhân quả có hedging khẳng định** ("có thể do", "được cho là bởi", "nhiều khả năng do", "theo một số chuyên gia, nguyên nhân là..."): vẫn là một khẳng định nhân quả (người viết nghiêng về tin quan hệ tồn tại), chỉ giảm độ chắc chắn — KHÔNG loại vì lý do thiếu chắc chắn. Phân biệt với hedging phủ định/trung lập ("không loại trừ khả năng X dẫn đến Y", "X có thể không làm tăng Y", "chưa rõ liệu X có gây ra Y hay không") — các câu này chủ động KHÔNG khẳng định quan hệ, chỉ nêu khả năng chưa xác định hoặc phủ định tác động, nên gán `non_causal`.
4. **Chuỗi nhân quả nhiều bước trong một câu** ("A khiến B, từ đó C"): tính là causal. Chỉ cần tồn tại ÍT NHẤT MỘT quan hệ A → B hợp lệ trong câu là đủ để gán `causal` — không yêu cầu toàn bộ câu phải mang nghĩa nhân quả.
5. **Nhân quả ngầm định, không có từ nối** (hai mệnh đề nối bằng dấu phẩy, không từ nối): CHỈ tính là causal khi thứ tự lý do → hệ quả là bắt buộc và không thể đọc theo hướng khác (liệt kê ngang hàng, đồng thời, trình tự thời gian). Đây là bar cao nhất trong toàn bộ hướng dẫn — nếu còn lưỡng lự dù chỉ một chút, gán `non_causal`. Lưu ý: bar cao không có nghĩa là hiếm khi đạt được — nhiều câu ngầm định rõ ràng (vd. "Thiếu vốn, năng suất sản xuất giảm") vẫn đạt bar này; bar chỉ loại các câu có thể đọc hợp lý theo hướng khác.
   **Test nhanh để áp dụng bar này nhất quán**: thử chèn "vì vậy" hoặc "do đó" vào giữa hai mệnh đề. Nếu câu vẫn tự nhiên và không đổi nghĩa, đó là dấu hiệu ủng hộ `causal`. Nếu chèn "và"/"đồng thời" vào cũng nghe tự nhiên không kém (câu đọc được như hai sự việc/xu hướng song song), đó là dấu hiệu lưỡng lự → `non_causal`.

### Các trường hợp KHÔNG tính là causal

- **Câu hỏi** về nguyên nhân/kết quả ("Vì sao...?", "Điều gì khiến...?") — không khẳng định.
- **Điều kiện/giả định thuần túy** ("nếu...thì", "giả sử", "trong trường hợp") khi sự việc chưa xảy ra và câu chỉ nêu giả thiết.
- **Tương quan/đồng thời không có chiều tác động** ("đi kèm với", "song song với", "liên quan đến") khi không có yếu tố nào rõ ràng là bên chủ động gây ra thay đổi ở bên kia.
- **Trình tự thời gian thuần túy** ("sau đó", "tiếp theo", "rồi") khi không có tín hiệu tác động, chỉ là chuỗi sự kiện theo thời gian.
- **Nhượng bộ/tương phản** ("mặc dù... nhưng...") khi câu đang phủ nhận hoặc làm yếu đi một quan hệ nhân quả kỳ vọng, không khẳng định quan hệ mới.
- **Phủ định quan hệ nhân quả mà KHÔNG tái khẳng định một quan hệ khác** ("X không gây ra Y", "không phải vì X mà Y xảy ra" khi không nêu nguyên nhân thay thế cụ thể). Lưu ý: cấu trúc "không phải do X mà do Y..." thường phủ định X nhưng đồng thời TÁI KHẲNG ĐỊNH một quan hệ khác (Y → kết quả) — trong trường hợp này, đánh giá quan hệ Y → kết quả theo các quy tắc thông thường ở trên, không tự động gán `non_causal` chỉ vì câu có cấu trúc phủ định.
- **Nhân quả ngầm định không đạt bar ở mục 5** (có thể đọc theo hướng khác ngoài nhân quả).

## Cách xác định has_explicit_trigger và trigger_text

- `has_explicit_trigger = true` CHỈ KHI quan hệ A → B được xác định NHỜ VÀO một từ/cụm từ nối nhân quả tường minh có mặt trong câu — tức từ đó thực sự là căn cứ cho quyết định causal, không phải chỉ xuất hiện đâu đó trong câu mà không liên quan đến quan hệ được xác định (vd. "Không rõ do đâu mà năng suất giảm" có chữ "do" nhưng câu này không xác định được A cụ thể nên gán `non_causal`, và `has_explicit_trigger` khi đó là `false` theo quy tắc bên dưới).
- `trigger_text` là MỘT chuỗi duy nhất (không phải danh sách) — chính từ/cụm từ nối làm căn cứ cho quyết định, giữ nguyên văn. Nếu quan hệ được thiết lập bởi cặp từ nối đi cùng nhau (vd. "do...nên..."), lấy từ đứng gần vế kết quả nhất (ở ví dụ này là "nên").
- `has_explicit_trigger = false` nếu câu được gán `causal` hoàn toàn dựa vào suy luận ngữ nghĩa/cấu trúc mà không có từ nối nhân quả nào làm căn cứ (trường hợp 5). `trigger_text` = null.
- Nếu `label = "non_causal"`, luôn đặt `has_explicit_trigger = false` và `trigger_text = null`.

## Ví dụ

| Câu | label | has_explicit_trigger | trigger_text | Lý do ngắn |
|---|---|---|---|---|
| "Giá phân bón tăng cao khiến chi phí sản xuất đội lên." | causal | true | "khiến" | A (giá phân bón tăng) tác động trực tiếp đến B (chi phí sản xuất). |
| "Nông dân lắp cảm biến độ ẩm để giảm chi phí tưới tiêu." | causal | true | "để" | Mệnh đề mục đích nêu trạng thái cụ thể (giảm chi phí) bị tác động, nên tính là causal. |
| "Thiếu vốn đầu tư, nhiều hộ nông dân không thể mua máy móc hiện đại." | causal | false | null | Không có từ nối, nhưng thứ tự lý do → hệ quả là bắt buộc, không đọc được theo hướng khác. |
| "Trung tâm mở lớp tập huấn, sau đó số hộ đăng ký tăng." | non_causal | false | null | Chỉ là trình tự thời gian, không có tín hiệu tác động rõ ràng giữa hai vế. |
| "Nếu được hỗ trợ vốn, nông dân sẽ dễ tiếp cận công nghệ hơn." | non_causal | false | null | Điều kiện giả định, sự việc chưa xảy ra. |
| "Vì sao nông dân chưa áp dụng công nghệ số?" | non_causal | false | null | Câu hỏi, không khẳng định quan hệ nhân quả. |
| "Mặc dù giá cao, nông dân vẫn mua." | non_causal | false | null | Nhượng bộ, phủ nhận quan hệ nhân quả kỳ vọng chứ không khẳng định quan hệ mới. |
| "Có thể do giá phân bón tăng nên chi phí sản xuất đội lên." | causal | true | "nên" | Nhân quả có hedging khẳng định vẫn tính là causal; trigger chọn từ gần vế kết quả nhất. |
| "Ứng dụng số đi kèm với năng suất cao hơn ở các hộ lớn." | non_causal | false | null | Tương quan, không rõ chiều tác động ai gây ra thay đổi cho ai. |
| "Nhiều yếu tố ảnh hưởng đến chuyển đổi số nông nghiệp." | non_causal | false | null | Có trigger "ảnh hưởng đến" nhưng A ("nhiều yếu tố") là cụm từ mơ hồ, không chỉ đích danh yếu tố nào. |
| "Ứng dụng IoT dẫn đến nhiều thay đổi tích cực." | non_causal | false | null | Có trigger nhưng B ("nhiều thay đổi tích cực") mơ hồ, không xác định thay đổi gì cụ thể. |
| "Nông dân đến hội thảo để nghe giới thiệu sản phẩm mới." | non_causal | false | null | Mệnh đề mục đích chỉ là hành động tiếp theo, không nêu trạng thái/kết quả nào bị tác động. |
| "Thiếu vốn, năng suất sản xuất của nhiều hộ giảm." | causal | false | null | Không có từ nối nhưng thứ tự lý do → hệ quả là bắt buộc, không đọc được theo hướng khác. |
| "Không loại trừ khả năng ứng dụng công nghệ số làm tăng chi phí ban đầu." | non_causal | false | null | Câu chủ động không khẳng định quan hệ, chỉ nêu khả năng chưa xác định (hedging trung lập, khác hedging khẳng định). |
| "Việc ứng dụng công nghệ này khiến năng suất tăng." | causal | true | "khiến" | A là cụm danh từ hóa hành động ("việc ứng dụng công nghệ"), có tiền ngữ rõ trong câu — không phải đại từ mơ hồ, vẫn hợp lệ làm A. |
| "Chi phí sản xuất tăng, nhiều hộ giảm diện tích canh tác." | non_causal | false | null | Test "vì vậy" và "và" đều chèn được tự nhiên như nhau — đọc được như hai xu hướng song song được báo cáo cùng nhau, không rõ ràng bắt buộc một chiều tác động → lưỡng lự → non_causal. |
| "Nông dân đầu tư hệ thống tưới để sản xuất lúa vụ đông." | non_causal | false | null | Mệnh đề mục đích ("sản xuất lúa vụ đông") là một hành động/mục tiêu, không phải trạng thái tăng/giảm/cải thiện nào bị tác động. |

## Đầu vào

$sentences

## Định dạng đầu ra

Chỉ trả về một mảng JSON hợp lệ theo đúng schema sau, một phần tử cho mỗi câu đầu vào, giữ đúng thứ tự:

[
  {
    "sentence": "...",
    "label": "causal",
    "has_explicit_trigger": true,
    "trigger_text": "một chuỗi duy nhất hoặc null",
    "reason": "..."
  }
]

## Quy tắc bắt buộc

* Mỗi phần tử đầu ra tương ứng với đúng một câu đầu vào, giữ nguyên thứ tự.
* `sentence` phải giữ nguyên nội dung câu đầu vào.
* `label` chỉ nhận giá trị `"causal"` hoặc `"non_causal"`.
* `reason` là một câu ngắn (dưới 20 từ) nêu rõ cặp A → B làm căn cứ quyết định (hoặc lý do không xác định được A/B nếu `non_causal`) — không chỉ lặp lại tên trigger. Ví dụ tốt: "Giá phân bón tăng tác động trực tiếp đến chi phí sản xuất." Ví dụ không tốt: "Có từ khiến nên là causal."
* Dùng JSON `null` khi giá trị không tồn tại hoặc không xác định được, không dùng chuỗi `"None"`, `"null"` hoặc chuỗi rỗng.
* Không giải thích kết quả ngoài field `reason`.
* Không thêm Markdown, không đặt JSON trong khối mã.
* Không thêm bất kỳ nội dung nào trước hoặc sau mảng JSON.

""")
