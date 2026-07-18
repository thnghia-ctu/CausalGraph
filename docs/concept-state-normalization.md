# Chuẩn hóa Causal Factor thành Concept và State

## 1. Mục tiêu

Bước chuẩn hóa factor không đơn thuần là cắt một phần chuỗi gốc, mà là một bài toán phân tích ngữ nghĩa nhỏ:

```text
Causal Factor Mention
        ↓
Concept Core + State
```

Ví dụ:

```text
nâng cao chất_lượng sản_phẩm
        ↓
concept: Chất lượng sản phẩm
state: Tăng
```

Trong ví dụ trên, `nâng cao → Tăng` là một phép chuẩn hóa ngữ nghĩa dựa trên từ điển, luật và cấu trúc cú pháp.

## 2. Kiến trúc xử lý đề xuất

Nên kết hợp ba tầng xử lý:

1. Chuẩn hóa bề mặt.
2. Nhận diện và chuẩn hóa biểu đạt trạng thái.
3. Trích xuất concept core theo cấu trúc cú pháp.

Sau khi có concept core, hệ thống tiếp tục ánh xạ nó vào controlled concept vocabulary.

```text
Factor Mention
    ↓
Surface Normalization
    ↓
State Detection
    ↓
Concept Core Extraction
    ↓
Concept Vocabulary Matching
    ↓
NormalizedFactor
```

## 3. Chuẩn hóa bề mặt

Ví dụ:

```text
nâng cao chất_lượng sản_phẩm
→ nâng cao chất lượng sản phẩm
```

Các thao tác có thể gồm:

- Thay dấu gạch dưới bằng khoảng trắng.
- Chuẩn hóa Unicode.
- Chuẩn hóa chữ hoa và chữ thường.
- Loại dấu câu, số thứ tự và từ đệm không cần thiết.
- Chuẩn hóa một số biến thể chính tả.

Kết quả của bước này chỉ phục vụ phân tích và so khớp. Trường `original_text` vẫn cần được giữ nguyên để truy vết.

## 4. Nhận diện State Expression

Xây dựng một `State Lexicon` ánh xạ nhiều cách diễn đạt về một state chuẩn.

```python
STATE_LEXICON = {
    "INCREASE": [
        "tăng",
        "gia tăng",
        "nâng cao",
        "tăng cường",
        "đẩy mạnh",
    ],
    "DECREASE": [
        "giảm",
        "giảm thiểu",
        "hạ thấp",
        "cắt giảm",
        "suy giảm",
    ],
    "LACK": [
        "thiếu",
        "không đủ",
        "thiếu hụt",
        "khan hiếm",
    ],
    "LIMITED": [
        "hạn chế",
        "bị giới hạn",
        "chưa đầy đủ",
        "không đáp ứng",
    ],
    "DIFFICULT": [
        "khó",
        "khó khăn",
        "gặp trở ngại",
        "khó tiếp cận",
    ],
    "HIGH": [
        "cao",
        "lớn",
        "đắt đỏ",
    ],
    "LOW": [
        "thấp",
        "kém",
        "yếu",
    ],
}
```

Nhãn hiển thị có thể là `Tăng`, `Giảm`, `Thiếu` hoặc `Hạn chế`, nhưng bên trong hệ thống nên sử dụng mã ổn định như `INCREASE`, `DECREASE`, `LACK` và `LIMITED`.

Không phải mọi biểu đạt gần nghĩa đều có thể ánh xạ cứng trong mọi ngữ cảnh. Chẳng hạn, `cải thiện` thường biểu diễn một thay đổi tích cực nhưng không phải lúc nào cũng tương đương trực tiếp với `INCREASE`:

```text
cải thiện chất lượng sản phẩm
→ Chất lượng sản phẩm + INCREASE
```

Trong khi đó:

```text
cải thiện tình trạng chi phí tăng cao
```

cần phân tích phạm vi tác động; không thể đơn giản kết luận `Chi phí + INCREASE`.

Vì vậy, mỗi mục từ nên đi kèm loại cấu trúc mà nó được phép áp dụng:

```python
StateRule(
    expression="nâng cao",
    normalized_state="INCREASE",
    pattern="state_verb_object",
)
```

## 5. Trích xuất Concept Core theo cấu trúc

Sau khi nhận diện state expression, hệ thống xác định thành phần mà state đang tác động. Dependency parsing có thể được dùng để tìm object hoặc noun phrase liên quan.

Ví dụ:

```text
nâng cao
└── object: chất lượng sản phẩm
```

Luật tương ứng:

```text
STATE_VERB + OBJECT
→ state = normalize(STATE_VERB)
→ concept candidate = OBJECT
```

Kết quả:

```text
nâng cao                  → INCREASE
chất lượng sản phẩm       → concept candidate
```

### 5.1. State đứng trước concept

```text
tăng năng_suất lao_động
giảm chi_phí sản_xuất
nâng cao chất_lượng sản_phẩm
thiếu nguồn nhân_lực
```

Luật:

```text
STATE_EXPRESSION + NOUN_PHRASE
→ state = normalize(STATE_EXPRESSION)
→ concept candidate = NOUN_PHRASE
```

### 5.2. State đứng sau concept

```text
chi_phí sản_xuất tăng cao
năng_suất lao_động thấp
hạ_tầng mạng còn hạn_chế
nguồn nhân_lực còn thiếu
```

Luật:

```text
NOUN_PHRASE + STATE_EXPRESSION
→ concept candidate = NOUN_PHRASE
→ state = normalize(STATE_EXPRESSION)
```

### 5.3. Cấu trúc có hoặc không có

```text
không có đủ kinh_phí
chưa có kỹ_năng số
có khả_năng tiếp_cận thị_trường
```

Ví dụ kết quả:

```text
không có đủ kinh phí
→ concept candidate = Kinh phí
→ state = LACK
```

```text
chưa có kỹ năng số
→ concept candidate = Kỹ năng số
→ state = LACK
```

### 5.4. Cấu trúc gặp khó khăn

```text
gặp khó_khăn về ngân_sách
gặp khó_khăn trong việc tiếp_cận thông_tin
```

Luật:

```text
gặp khó khăn về X
→ concept candidate = X
→ state = DIFFICULT
```

```text
gặp khó khăn trong việc X
→ concept candidate = X
→ state = DIFFICULT
```

Ví dụ:

```text
gặp khó khăn trong việc tiếp cận thông tin
→ concept candidate = Tiếp cận thông tin
→ state = DIFFICULT
```

Concept có thể là một hoạt động hoặc sự kiện, không nhất thiết chỉ là một danh từ đơn.

## 6. Xử lý phủ định và mức độ

Các biểu đạt sau không nên bị làm mất thông tin:

```text
không tăng năng_suất
chưa cải_thiện chất_lượng
giảm mạnh chi_phí
năng_suất tăng đáng_kể
```

Model có thể được mở rộng thành:

```python
from dataclasses import dataclass


@dataclass
class NormalizedFactor:
    original_text: str
    concept: str
    state: str | None
    negated: bool = False
    intensity: str | None = None
```

Ví dụ:

```text
không tăng năng suất
→ concept = Năng suất
→ state = INCREASE
→ negated = True
```

```text
giảm mạnh chi phí
→ concept = Chi phí
→ state = DECREASE
→ intensity = STRONG
```

Không nên tự động chuyển `không tăng` thành `giảm`, vì hai biểu đạt này không tương đương.

## 7. Chuẩn hóa Concept Core

Sau khi tách state, các concept candidate vẫn có thể là những cách diễn đạt khác nhau của cùng một concept:

```text
nâng cao chất lượng sản phẩm → chất lượng sản phẩm
cải thiện chất lượng nông sản → chất lượng nông sản
gia tăng chất lượng đầu ra   → chất lượng đầu ra
```

Các candidate trên có thể được ánh xạ về:

```text
Concept: Chất lượng sản phẩm nông nghiệp
```

Cần tách riêng hai tài nguyên:

```text
State Lexicon
nâng cao, gia tăng, tăng cường → INCREASE
```

```text
Concept Alias Vocabulary
chất lượng nông sản
chất lượng đầu ra
chất lượng sản phẩm nông nghiệp
→ C_PRODUCT_QUALITY
```

Không nên trộn state lexicon và concept alias vocabulary vào cùng một từ điển.

Việc ánh xạ concept nên thực hiện theo thứ tự:

1. Exact match với preferred label.
2. Exact match với alias đã được duyệt.
3. Semantic matching bằng embedding để sinh gợi ý.
4. Chuyên gia duyệt nếu chưa đủ chắc chắn.

## 8. Luồng xử lý minh họa

Đầu vào:

```text
nâng cao chất_lượng sản_phẩm nông_nghiệp
```

Quá trình xử lý:

```text
1. Surface normalization
   → nâng cao chất lượng sản phẩm nông nghiệp

2. State matching
   → expression = nâng cao
   → state = INCREASE

3. Dependency/rule extraction
   → concept candidate = chất lượng sản phẩm nông nghiệp

4. Exact alias lookup
   → C_PRODUCT_QUALITY

5. Nếu không exact match
   → tìm top-k concept bằng embedding

6. Nếu độ tương đồng đủ cao
   → gợi ý concept để chuyên gia duyệt

7. Kết quả
   → concept_id = C_PRODUCT_QUALITY
   → state = INCREASE
```

Pseudo-code:

```python
def normalize_factor(text, vocabulary):
    normalized_text = normalize_surface(text)

    state_match = state_parser.parse(normalized_text)

    if state_match:
        concept_candidate = concept_extractor.extract(
            normalized_text,
            state_match,
        )
    else:
        concept_candidate = normalized_text

    concept = vocabulary.exact_match(concept_candidate)

    if concept is None:
        concept = vocabulary.semantic_match(concept_candidate)

    return NormalizedFactor(
        original_text=text,
        concept=concept.preferred_label,
        state=state_match.normalized_state if state_match else None,
    )
```

Trong triển khai thực tế, `semantic_match` nên trả về cả score và trạng thái cần duyệt, thay vì luôn tự động chấp nhận concept gần nhất.

## 9. Vai trò của Rule, Embedding và LLM

Kiến trúc phù hợp cho phạm vi luận văn là kiến trúc lai:

- Rule và lexicon dùng để nhận diện state, vì dễ giải thích và đánh giá.
- Dependency parsing dùng để xác định phạm vi tác động của state.
- Controlled vocabulary và alias dùng để ánh xạ các trường hợp đã biết.
- Embedding dùng để tìm concept tương đồng và sinh gợi ý.
- Chuyên gia xác nhận các trường hợp chưa chắc chắn.
- LLM có thể dùng để sinh gợi ý hoặc làm baseline so sánh, nhưng không nên là nguồn quyết định duy nhất.

State trong miền dữ liệu tương đối hữu hạn nên có thể kiểm soát tốt bằng rule. Phần mở và khó hơn là ánh xạ `concept_candidate` vào controlled concept vocabulary.

## 10. Kết luận

Phép biến đổi:

```text
nâng cao chất lượng sản phẩm
→ Chất lượng sản phẩm + Tăng
```

được tạo bởi một luật ngữ nghĩa và cú pháp:

```text
[nâng cao]STATE_VERB [chất lượng sản phẩm]OBJECT
```

Sau đó, `Chất lượng sản phẩm` tiếp tục được ánh xạ vào controlled vocabulary bằng preferred label, alias và embedding. Vì vậy, toàn bộ bước chuẩn hóa gồm hai bài toán liên tiếp:

```text
Factor Mention
→ Concept Candidate + State
→ Controlled Concept + State
```
