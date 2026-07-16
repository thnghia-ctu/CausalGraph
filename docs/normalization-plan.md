# Đề xuất bước tiếp theo của hệ thống trích xuất quan hệ nhân quả

## 1. Những gì hệ thống đã thực hiện

Hiện tại, hệ thống đã xây dựng được pipeline trích xuất quan hệ nhân quả từ văn bản tiếng Việt theo hướng rule-based kết hợp phân tích phụ thuộc (dependency parsing).

Quy trình hiện tại gồm các bước chính:

```text
Văn bản
    ↓
Tiền xử lý
    ↓
Phân tích phụ thuộc (VnCoreNLP)
    ↓
Nhận diện trigger nhân quả
    ↓
Áp dụng các structural pattern
    ↓
Trích xuất Relation
```

Đầu ra của hệ thống hiện nay là các quan hệ nhân quả dưới dạng:

```text
Relation(
    source,
    trigger,
    relationship,
    target
)
```

Ví dụ:

```text
Source:
thiếu vốn đầu tư

Trigger:
cản trở

Target:
quá trình chuyển đổi số
```

Bước này đã giải quyết được bài toán nhận diện và trích xuất các quan hệ nhân quả từ văn bản.

## 2. Hạn chế của đầu ra hiện tại

Mặc dù `Relation` đã mô tả đúng quan hệ nhân quả trong từng câu, `source` và `target` vẫn là các cụm từ gốc trong văn bản.

Ví dụ:

- `thiếu vốn`
- `không đủ kinh phí`
- `nguồn lực tài chính hạn chế`
- `khó tiếp cận vốn`

Các cụm này hiện đều được xem là những node khác nhau.

Nếu xây dựng causal graph trực tiếp từ các cụm này sẽ dẫn đến:

- Số lượng node rất lớn.
- Nhiều node biểu diễn cùng một ý nghĩa.
- Đồ thị bị phân mảnh.
- Khó phân tích các yếu tố chính.

## 3. Bài toán còn thiếu

Sau khi trích xuất `Relation`, hệ thống vẫn chưa biết hai cụm từ khác nhau có đang nói về cùng một yếu tố hay không.

Nói cách khác, hệ thống hiện nay mới trả lời được:

> Quan hệ nhân quả là gì?

Nhưng chưa trả lời được:

> Yếu tố nhân quả này thực chất là khái niệm nào?

Ví dụ:

- `thiếu vốn`
- `không đủ kinh phí`
- `nguồn lực tài chính hạn chế`

Con người hiểu đây đều là các biểu đạt liên quan đến một vấn đề tài chính, trong khi máy tính hiện xem chúng là ba node độc lập.

## 4. Bài toán đề xuất

Từ hạn chế trên, đề xuất bổ sung một bước mới sau Relation Extraction:

```text
Relation Extraction
        ↓
Causal Factor Normalization
        ↓
Causal Graph
```

Mục tiêu của bước này là chuẩn hóa các biểu đạt khác nhau về cùng một yếu tố nhân quả thành một biểu diễn thống nhất, phục vụ xây dựng causal graph.

Đây là bài toán nằm trong hướng nghiên cứu **Concept Normalization**, nhưng được chuyên biệt hóa cho các yếu tố nhân quả. Vì vậy, tên đề xuất của bài toán là:

> **Causal Factor Concept Normalization**

## 5. Quan điểm thiết kế

Điểm quan trọng của bước này là không chuẩn hóa toàn bộ câu, mà chỉ chuẩn hóa:

- `source`
- `target`

đã được Relation Extraction trích ra.

Đơn vị xử lý không còn là câu, mà là:

> **Causal Factor Mention**

Ví dụ:

- `thiếu vốn đầu tư`
- `chi phí công nghệ cao`
- `khó tiếp cận tín dụng`

## 6. Ý tưởng xây dựng Concept

Qua khảo sát ban đầu, trong dữ liệu tồn tại nhiều cách diễn đạt khác nhau nhưng đề cập cùng một vấn đề.

Ví dụ:

```text
thiếu vốn
không đủ kinh phí
nguồn lực tài chính hạn chế
```

Các biểu đạt này thực chất đều liên quan đến:

```text
Concept: Vốn đầu tư
```

Do đó, đề xuất xây dựng một **Controlled Concept Vocabulary**.

Khác với ontology đầy đủ, controlled vocabulary chỉ gồm một tập hữu hạn các khái niệm chuẩn của miền nghiên cứu.

Các concept không được định nghĩa hoàn toàn từ trước, mà được xây dựng theo hướng bottom-up:

1. Thu thập `source` và `target` từ dữ liệu.
2. Nhóm các biểu đạt đồng nghĩa hoặc gần đồng nghĩa.
3. Đặt tên concept đại diện.
4. Chuyên gia xác nhận.

Ví dụ:

```text
thiếu vốn
không đủ kinh phí
nguồn lực tài chính hạn chế

        ↓

Concept: Vốn đầu tư
```

## 7. Ý tưởng xây dựng Category

Sau khi đã có tập concept, các concept tiếp tục được nhóm thành các nhóm cấp cao hơn.

Ví dụ:

```text
Concept:
- Vốn đầu tư
- Chi phí công nghệ
- Tiếp cận tín dụng

        ↓

Category: Tài chính và chi phí
```

Trong đó:

- **Concept** dùng để xây dựng node của causal graph.
- **Category** chỉ dùng để thống kê, phân tích, trực quan hóa và hỗ trợ chuyên gia.
- Category không thay thế concept.

## 8. Đầu ra đề xuất

Sau bước chuẩn hóa, mỗi `source` hoặc `target` được biểu diễn dưới dạng:

```text
NormalizedFactor(
    original_text,
    concept,
    state
)
```

Ví dụ:

```text
original_text:
nông dân thiếu kỹ năng số

        ↓

concept:
Kỹ năng số

        ↓

state:
Thiếu
```

Node cuối cùng của causal graph được tạo từ:

```text
Concept + State
```

Ví dụ:

```text
Thiếu kỹ năng số
```

thay vì dùng nguyên văn:

```text
nông dân thiếu kỹ năng số
```

## 9. Lộ trình thực hiện

### Giai đoạn 1 — Thu thập factor mention

Thu thập toàn bộ `source` và `target` từ hệ thống hiện tại.

### Giai đoạn 2 — Thống kê biểu đạt

Thống kê các biểu đạt xuất hiện nhiều.

### Giai đoạn 3 — Nhóm biểu đạt

Nhóm các biểu đạt đồng nghĩa thành concept bằng:

- Luật.
- Từ điển synonym.
- Embedding hỗ trợ gợi ý.

### Giai đoạn 4 — Xây dựng concept vocabulary

Xây dựng tập concept chuẩn.

### Giai đoạn 5 — Xây dựng category

Nhóm các concept thành category.

### Giai đoạn 6 — Chuẩn hóa Relation

Chuẩn hóa toàn bộ `Relation` dựa trên controlled concept vocabulary.

### Giai đoạn 7 — Sinh causal graph

Sinh causal graph từ các concept đã được chuẩn hóa.

## 10. Lý do lựa chọn hướng này

Không đề xuất xây dựng ontology hoàn chỉnh ngay từ đầu, vì:

- Số lượng khái niệm chưa lớn.
- Ontology đòi hỏi nhiều công sức xây dựng và bảo trì.
- Việc xây dựng ontology đầy đủ vượt quá phạm vi của luận văn.

Thay vào đó, đề xuất bắt đầu bằng một controlled vocabulary được xây dựng trực tiếp từ dữ liệu thực tế.

Cách tiếp cận này có các ưu điểm:

- Phù hợp với quy mô luận văn.
- Dễ giải thích.
- Dễ đánh giá.
- Có thể mở rộng dần thành ontology trong các nghiên cứu tiếp theo nếu cần.
