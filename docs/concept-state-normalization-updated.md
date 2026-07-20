# Chuẩn hóa Causal Factor thành Concept và State

## 1. Mục tiêu

Bước chuẩn hóa causal factor không đơn thuần là cắt một phần chuỗi gốc, mà là một bài toán phân tích ngữ nghĩa nhằm biến một cách diễn đạt cụ thể trong văn bản thành một biểu diễn ổn định, có thể dùng để gom nhóm node và xây dựng đồ thị nhân quả.

```text
Causal Factor Mention
        ↓
Concept Candidate + State
        ↓
Controlled Concept + State
```

Ví dụ:

```text
nâng cao chất_lượng sản_phẩm
        ↓
concept: Chất lượng sản phẩm
state: INCREASE
```

Trong ví dụ trên:

- `nâng cao` là biểu đạt trạng thái, được chuẩn hóa thành `INCREASE`.
- `chất lượng sản phẩm` là concept core.
- Concept core tiếp tục được ánh xạ vào một concept có mã ổn định trong controlled vocabulary.

Mục tiêu cuối cùng là giảm sự phân mảnh của đồ thị. Các biểu đạt như `nâng cao chất lượng nông sản`, `chất lượng sản phẩm tăng` và `cải thiện chất lượng đầu ra` có thể được xem xét ánh xạ về cùng một concept, nhưng vẫn phải giữ lại trạng thái và thông tin truy vết riêng.

## 2. Nguyên tắc thiết kế cốt lõi

### 2.1. Tách biệt Concept, State và Relation

Ba thành phần này có vai trò khác nhau và không nên trộn lẫn:

```text
Concept  = thực thể, thuộc tính, hoạt động hoặc hiện tượng đang được nói đến
State    = trạng thái hoặc sự thay đổi của concept
Relation = quan hệ nhân quả giữa hai factor
```

Ví dụ:

```text
Chi phí tăng làm lợi nhuận giảm
```

Có thể biểu diễn thành:

```text
Source:
    concept = Chi phí
    state   = INCREASE

Relation:
    type    = CAUSE

Target:
    concept = Lợi nhuận
    state   = DECREASE
```

Không nên tạo các concept như `Chi phí tăng`, `Chi phí cao`, `Chi phí giảm`. Các biểu đạt này phải cùng quy về concept trung tính `Chi phí`, còn phần tăng, cao hoặc giảm được lưu trong State.

### 2.2. Concept core phải ở dạng trung tính

Concept core không chứa chiều tăng, giảm, cao, thấp, thiếu hoặc đủ.

```text
chi phí cao       → Concept: Chi phí; State: HIGH
chi phí tăng      → Concept: Chi phí; State: INCREASE
chi phí thấp      → Concept: Chi phí; State: LOW
chi phí giảm      → Concept: Chi phí; State: DECREASE
```

Nguyên tắc này giúp tất cả biểu đạt cùng trỏ về một node concept ổn định.

### 2.3. Không đồng nhất State với tốt hoặc xấu

`INCREASE` và `DECREASE` chỉ mô tả chiều thay đổi, không tự mang ý nghĩa tích cực hoặc tiêu cực.

```text
Năng suất + INCREASE → thường được xem là tích cực
Chi phí + INCREASE   → thường được xem là tiêu cực
```

Việc đánh giá tốt hoặc xấu phụ thuộc concept, mục tiêu và góc nhìn tác nhân. Vì vậy, không đưa `polarity` tốt/xấu vào State.

### 2.4. `desired_direction` không thuộc phần lõi

Chiều mong muốn không phải lúc nào cũng là thuộc tính tuyệt đối của concept.

Ví dụ:

```text
Giá nông sản
```

- Người nông dân có thể mong muốn giá cao.
- Người tiêu dùng có thể mong muốn giá thấp.

Do đó, `desired_direction` chỉ nên là metadata tùy chọn, đi kèm perspective hoặc actor nếu luận văn cần diễn giải sâu hơn.

```text
desired_direction(concept, perspective)
```

Nó không cần thiết để dựng đồ thị nhân quả ở bước lõi.

## 3. Kiến trúc xử lý đề xuất

Kiến trúc nên kết hợp rule, lexicon, dependency parsing, embedding và chuyên gia:

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
Confidence and Review Decision
    ↓
NormalizedFactor
```

Vai trò của từng thành phần:

- Rule và lexicon: xử lý các cấu trúc phổ biến, dễ giải thích và ổn định.
- POS và vị trí state expression: xác định ranh giới concept trong các factor ngắn.
- Dependency parsing: hỗ trợ khi cấu trúc phức tạp hoặc rule bề mặt không đủ.
- Controlled vocabulary và alias: ánh xạ các trường hợp đã biết.
- Embedding: sinh ứng viên concept gần nghĩa.
- Chuyên gia: xác nhận các trường hợp không chắc chắn.

Dependency parsing không nên là nền tảng duy nhất vì parser tiếng Việt có thể sai trên văn bản chuyên ngành. Với các factor ngắn, rule dựa trên POS và vị trí state expression nên được ưu tiên; dependency parsing là tầng hỗ trợ hoặc fallback.

## 4. Chuẩn hóa bề mặt

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
- Chuẩn hóa khoảng trắng.
- Chuẩn hóa một số biến thể chính tả đã được xác nhận.

Kết quả của bước này chỉ dùng cho phân tích và so khớp. `original_text` luôn được giữ nguyên để truy vết và đánh giá lỗi.

## 5. Mô hình State

### 5.1. Không xem mọi State là chiều thay đổi

State nên chia ít nhất thành hai nhóm.

#### A. Trạng thái động — CHANGE

Mô tả sự biến đổi theo thời gian:

```text
INCREASE
DECREASE
IMPROVE
DETERIORATE
```

Ví dụ:

```text
chi phí tăng       → CHANGE / INCREASE
năng suất giảm     → CHANGE / DECREASE
chất lượng cải thiện → CHANGE / IMPROVE
```

#### B. Trạng thái tĩnh hoặc điều kiện — CONDITION

Mô tả mức độ hoặc điều kiện hiện tại:

```text
HIGH
LOW
LACK
SUFFICIENT
LIMITED
DIFFICULT
AVAILABLE
UNAVAILABLE
```

Ví dụ:

```text
chi phí cao          → CONDITION / HIGH
năng suất thấp       → CONDITION / LOW
thiếu vốn            → CONDITION / LACK
có đủ kinh phí       → CONDITION / SUFFICIENT
khó tiếp cận vốn     → CONDITION / DIFFICULT
hạ tầng hạn chế      → CONDITION / LIMITED
```

Phân biệt này rất quan trọng:

```text
chi phí tăng ≠ chi phí cao
```

`INCREASE` mô tả biến động; `HIGH` mô tả mức hiện tại. Không nên gộp hai state này.

### 5.2. State Lexicon

Xây dựng `State Lexicon` ánh xạ nhiều cách diễn đạt về một state chuẩn.

```python
STATE_LEXICON = {
    "INCREASE": (
        "tăng",
        "gia tăng",
        "nâng cao",
        "tăng cường",
        "đẩy mạnh",
    ),
    "DECREASE": (
        "giảm",
        "giảm thiểu",
        "hạ thấp",
        "cắt giảm",
        "suy giảm",
    ),
    "LACK": (
        "thiếu",
        "không đủ",
        "thiếu hụt",
        "khan hiếm",
        "chưa có",
    ),
    "SUFFICIENT": (
        "đủ",
        "có đủ",
        "đầy đủ",
        "đáp ứng đủ",
    ),
    "LIMITED": (
        "hạn chế",
        "bị giới hạn",
        "chưa đầy đủ",
        "không đáp ứng",
    ),
    "DIFFICULT": (
        "khó",
        "khó khăn",
        "gặp trở ngại",
        "khó tiếp cận",
    ),
    "HIGH": (
        "cao",
        "lớn",
        "đắt đỏ",
    ),
    "LOW": (
        "thấp",
        "kém",
        "yếu",
    ),
}
```

Mã nội bộ phải ổn định như `INCREASE`, `DECREASE`, `LACK`; nhãn tiếng Việt chỉ dùng để hiển thị.

### 5.3. Rule có điều kiện theo cấu trúc

Không phải mọi từ gần nghĩa đều ánh xạ cứng trong mọi ngữ cảnh.

```text
cải thiện chất lượng sản phẩm
→ Chất lượng sản phẩm + IMPROVE
```

Nhưng:

```text
cải thiện tình trạng chi phí tăng cao
```

không thể đơn giản tách thành `Chi phí + INCREASE`, vì `cải thiện` tác động lên cả tình trạng tiêu cực, không trực tiếp làm tăng chi phí.

Mỗi state expression nên đi kèm điều kiện áp dụng:

```python
@dataclass(frozen=True)
class StateRule:
    expression: str
    state_category: str
    state_value: str
    pattern: str
    allowed_pos: tuple[str, ...] = ()
```

Ví dụ:

```python
StateRule(
    expression="nâng cao",
    state_category="CHANGE",
    state_value="INCREASE",
    pattern="state_verb_object",
    allowed_pos=("V",),
)
```

## 6. Trích xuất Concept Core

### 6.1. Thứ tự ưu tiên

Đề xuất ưu tiên:

1. Rule bề mặt dựa trên state expression và vị trí.
2. Rule kết hợp POS để xác định noun phrase hoặc verb phrase.
3. Dependency parsing để mở rộng hoặc xử lý câu phức.
4. Fallback bảo thủ nếu chưa xác định chắc chắn.

### 6.2. State đứng trước concept

```text
tăng năng_suất lao_động
giảm chi_phí sản_xuất
nâng cao chất_lượng sản_phẩm
thiếu nguồn nhân_lực
```

Luật:

```text
STATE_EXPRESSION + CONCEPT_PHRASE
→ state = normalize(STATE_EXPRESSION)
→ concept candidate = CONCEPT_PHRASE
```

### 6.3. State đứng sau concept

```text
chi_phí sản_xuất tăng cao
năng_suất lao_động thấp
hạ_tầng mạng còn hạn_chế
nguồn nhân_lực còn thiếu
```

Luật:

```text
CONCEPT_PHRASE + STATE_EXPRESSION
→ concept candidate = CONCEPT_PHRASE
→ state = normalize(STATE_EXPRESSION)
```

### 6.4. Cấu trúc có hoặc không có

```text
không có đủ kinh_phí
chưa có kỹ_năng số
có đủ nguồn_lực
có khả_năng tiếp_cận thị_trường
```

Ví dụ:

```text
không có đủ kinh phí
→ concept candidate = Kinh phí
→ state = LACK
```

```text
có đủ nguồn lực
→ concept candidate = Nguồn lực
→ state = SUFFICIENT
```

Không nên mặc định mọi cấu trúc `có X` là `SUFFICIENT`. Cần phân biệt:

```text
có đủ vốn         → SUFFICIENT
có vốn            → AVAILABLE hoặc state = None, tùy schema
có khả năng X     → concept có thể là Khả năng X, không nhất thiết là SUFFICIENT
```

### 6.5. Cấu trúc gặp khó khăn

```text
gặp khó khăn về ngân_sách
gặp khó khăn trong việc tiếp_cận thông_tin
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

Concept có thể là hoạt động hoặc sự kiện, không nhất thiết chỉ là danh từ:

```text
tiếp cận thông tin
ứng dụng công nghệ
tham gia thị trường
```

### 6.6. Dependency parsing là tầng hỗ trợ

Ví dụ đơn giản:

```text
nâng cao chất lượng sản phẩm
```

Rule bề mặt đã đủ để xác định:

```text
state expression = nâng cao
concept candidate = chất lượng sản phẩm
```

Ví dụ phức tạp:

```text
Việc ứng dụng IoT giúp người nông dân nâng cao chất lượng sản phẩm.
```

Dependency parsing có thể hỗ trợ xác định `chất lượng sản phẩm` là object của `nâng cao`. Tuy nhiên, nếu parser cho nhãn sai, hệ thống vẫn cần fallback dựa trên vị trí state expression, POS và giới hạn cụm.

## 7. Phủ định và mức độ

### 7.1. Phủ định

Không nên tự động chuyển:

```text
không tăng → giảm
```

vì hai biểu đạt không tương đương.

```text
không tăng năng suất
→ concept = Năng suất
→ state = INCREASE
→ negated = True
```

Tương tự:

```text
chưa cải thiện chất lượng
→ concept = Chất lượng
→ state = IMPROVE
→ negated = True
```

## 8. Chuẩn hóa Concept Core

### 8.1. Controlled Concept Vocabulary

Sau khi tách state, concept candidate vẫn có nhiều cách diễn đạt:

```text
chất lượng sản phẩm
chất lượng nông sản
chất lượng đầu ra
chất lượng sản phẩm nông nghiệp
```

Controlled vocabulary có thể lưu:

```text
concept_id: C_PRODUCT_QUALITY
preferred_label: Chất lượng sản phẩm nông nghiệp
aliases:
    - chất lượng sản phẩm
    - chất lượng nông sản
```

Không nên tự động coi `chất lượng đầu ra` là đồng nghĩa trong mọi ngữ cảnh. Alias chỉ được thêm khi đã kiểm tra ngữ nghĩa và phạm vi miền.

### 8.2. Tách riêng State Lexicon và Concept Alias Vocabulary

```text
State Lexicon
nâng cao, gia tăng, tăng cường → INCREASE
```

```text
Concept Alias Vocabulary
chất lượng nông sản
chất lượng sản phẩm
→ C_PRODUCT_QUALITY
```

Hai tài nguyên này có mục đích khác nhau và không được trộn vào cùng một bảng.

### 8.3. Thứ tự ánh xạ concept

Thực hiện theo thứ tự:

1. Exact match với `preferred_label`.
2. Exact match với alias đã được duyệt.
3. Semantic matching bằng embedding để lấy top-k ứng viên.
4. Tự động chấp nhận chỉ khi vượt ngưỡng tin cậy cao.
5. Đưa chuyên gia duyệt khi score nằm trong vùng xám.
6. Gắn `UNMAPPED` hoặc tạo ứng viên concept mới khi không có kết quả phù hợp.

### 8.4. Ưu tiên under-merging

Khi chưa chắc chắn, nên ưu tiên tách hơn gộp.

```text
Under-merging: hai node gần nghĩa chưa được gộp
Over-merging: hai concept khác nghĩa bị gộp thành một
```

Trong luận văn, over-merging nguy hiểm hơn vì làm sai cấu trúc ngữ nghĩa của graph. Vì vậy, ngưỡng tự động nên bảo thủ và các trường hợp vùng xám phải được chuyên gia duyệt.

## 9. Chính sách OOV và No-match

Một concept candidate có thể không xuất hiện trong vocabulary và cũng không đủ gần với các concept hiện có.

Ví dụ:

```text
mức độ số hóa chuỗi cung ứng
```

Quy trình:

```text
Exact match: không có
        ↓
Alias match: không có
        ↓
Embedding top-k: score thấp
        ↓
UNMAPPED + needs_review = True
```

Có thể áp dụng một trong hai chính sách:

- Tạo `concept proposal` mới chờ chuyên gia duyệt.
- Giữ `UNMAPPED` nhưng vẫn lưu concept candidate gốc.

Không được ép candidate vào concept gần nhất chỉ vì hệ thống luôn cần một kết quả.

## 10. Mô hình dữ liệu đề xuất

### 10.1. State

```python
from dataclasses import dataclass
from typing import Literal

StateCategory = Literal["CHANGE", "CONDITION"]

StateValue = Literal[
    "INCREASE",
    "DECREASE",
    "HIGH",
    "LOW",
    "LACK",
    "SUFFICIENT",
    "LIMITED",
    "DIFFICULT",
    "AVAILABLE",
    "UNAVAILABLE",
]


@dataclass(frozen=True)
class State:
    category: StateCategory
    value: StateValue
    expression: str
    negated: bool = False
```

`expression` lưu biểu đạt đã khớp như `nâng cao`, `không đủ`, `còn hạn chế` để phục vụ truy vết.

### 10.2. NormalizedFactor

```python
@dataclass
class NormalizedFactor:
    original_text: str
    normalized_text: str

    concept_candidate: str
    concept_id: str | None
    concept_label: str | None

    state: State | None

    confidence: float
    mapping_method: Literal[
        "preferred_label",
        "alias",
        "embedding",
        "unmapped",
    ]
    needs_review: bool = False
```

Giải thích:

- `original_text`: chuỗi gốc để truy vết.
- `normalized_text`: chuỗi sau chuẩn hóa bề mặt.
- `concept_candidate`: concept core được trích xuất từ factor.
- `concept_id`: ID ổn định để dựng graph.
- `concept_label`: nhãn hiển thị.
- `state`: trạng thái đã tách khỏi concept.
- `confidence`: độ tin cậy của toàn bộ kết quả hoặc bước mapping.
- `mapping_method`: phương pháp ánh xạ concept.
- `needs_review`: có cần chuyên gia xác nhận hay không.

Không đưa `desired_direction` vào `NormalizedFactor` vì đây không phải thông tin trực tiếp của factor mention.

### 10.3. Metadata tùy chọn theo perspective

Chỉ bổ sung nếu mục tiêu nghiên cứu cần diễn giải tốt/xấu:

```python
@dataclass(frozen=True)
class ConceptPreference:
    concept_id: str
    perspective: str
    desired_direction: Literal["HIGH", "LOW", "BALANCED"]
```

Ví dụ:

```text
concept_id = C_CROP_PRICE
perspective = FARMER
preferred_direction = HIGH
```

```text
concept_id = C_CROP_PRICE
perspective = CONSUMER
preferred_direction = LOW
```

## 11. Luồng xử lý minh họa

Đầu vào:

```text
nâng cao chất_lượng sản_phẩm nông_nghiệp
```

Quá trình:

```text
1. Surface normalization
   → nâng cao chất lượng sản phẩm nông nghiệp

2. State matching
   → expression = nâng cao
   → category = CHANGE
   → value = INCREASE

3. Rule/POS extraction
   → concept candidate = chất lượng sản phẩm nông nghiệp

4. Exact preferred-label lookup
   → C_PRODUCT_QUALITY

5. Kết quả
   → concept_id = C_PRODUCT_QUALITY
   → concept_label = Chất lượng sản phẩm nông nghiệp
   → state = CHANGE / INCREASE
   → mapping_method = preferred_label
   → needs_review = False
```

Ví dụ không map được:

```text
mức độ số hóa chuỗi cung ứng tăng
```

```text
1. state = CHANGE / INCREASE
2. concept candidate = mức độ số hóa chuỗi cung ứng
3. exact/alias = không có
4. embedding top-1 = 0.54
5. dưới ngưỡng chấp nhận
6. concept_id = None
7. mapping_method = unmapped
8. needs_review = True
```

## 12. Pseudo-code đề xuất

```python
def normalize_factor(text: str, vocabulary) -> NormalizedFactor:
    normalized_text = normalize_surface(text)

    state_match = state_parser.parse(normalized_text)

    concept_candidate = concept_extractor.extract(
        text=normalized_text,
        state_match=state_match,
        strategy=("rule", "pos", "dependency", "fallback"),
    )

    mapping = vocabulary.exact_match(concept_candidate)

    if mapping is None:
        candidates = vocabulary.semantic_search(
            concept_candidate,
            top_k=5,
        )
        mapping = mapping_policy.decide(candidates)

    return NormalizedFactor(
        original_text=text,
        normalized_text=normalized_text,
        concept_candidate=concept_candidate,
        concept_id=mapping.concept_id,
        concept_label=mapping.preferred_label,
        state=state_match.state if state_match else None,
        confidence=mapping.confidence,
        mapping_method=mapping.method,
        needs_review=mapping.needs_review,
    )
```

`semantic_search` chỉ sinh ứng viên. Quyết định chấp nhận, duyệt hoặc từ chối phải do `mapping_policy` thực hiện.

## 13. Quan hệ với Causal Graph

Dữ liệu cốt lõi để dựng graph gồm:

```text
Source Concept + Source State
        ↓ Relation
Target Concept + Target State
```

Ví dụ:

```text
Thiếu vốn làm giảm quy mô sản xuất
```

```text
Source:
    concept = Vốn
    state = CONDITION / LACK

Relation:
    type = CAUSE

Target:
    concept = Quy mô sản xuất
    state = CHANGE / DECREASE
```

Graph có thể sử dụng `concept_id` làm node ID ổn định. State có thể được lưu dưới dạng:

- thuộc tính của mention;
- thuộc tính của edge evidence;
- hoặc node trạng thái riêng nếu mô hình graph yêu cầu.

Không cần `desired_direction` để tạo node và mũi tên. Metadata này chỉ cần khi muốn giải thích tác động theo góc nhìn một chủ thể cụ thể.

## 14. Khung đánh giá

### 14.1. Gold standard

Xây dựng một tập dữ liệu thủ công gồm vài trăm factor mention, được gán:

```text
original_text
concept_candidate
concept_id
state_category
state_value
negated
```

Nên có ít nhất hai người gán nhãn cho một phần dữ liệu để kiểm tra mức độ nhất quán.

### 14.2. Đánh giá State Detection

Các metric phù hợp:

- Precision, Recall, F1 cho nhận diện state expression.
- Accuracy hoặc macro-F1 cho `state_value`.
- F1 riêng cho các nhãn quan trọng như `INCREASE`, `DECREASE`, `LACK`, `LIMITED`.
- Accuracy cho `negated`.

### 14.3. Đánh giá Concept Core Extraction

Có thể dùng:

- Exact span match.
- Token-level Precision, Recall, F1.
- Error analysis theo loại cấu trúc.

So sánh ít nhất:

```text
Rule/POS only
Dependency only
Rule/POS + Dependency fallback
```

### 14.4. Đánh giá Concept Mapping

Các metric:

- Top-1 accuracy.
- Top-k recall.
- Tỷ lệ tự động ánh xạ đúng.
- Tỷ lệ `needs_review`.
- Tỷ lệ `UNMAPPED`.
- Tỷ lệ over-merging và under-merging qua phân tích lỗi.

### 14.5. Baseline

Có thể so sánh hệ đề xuất với:

- Exact/alias only.
- Embedding nearest-neighbor không có rule.
- LLM zero-shot hoặc few-shot.
- Hệ lai rule + embedding + expert.

Mục tiêu không nhất thiết là chứng minh hệ lai có accuracy cao nhất tuyệt đối, mà có thể chứng minh sự cân bằng giữa độ chính xác, khả năng giải thích, kiểm soát và chi phí hiệu chỉnh.

## 15. Phạm vi luận văn đề xuất

### Bắt buộc

- Surface normalization.
- State lexicon và rule.
- Phân loại State thành CHANGE và CONDITION.
- Concept core extraction bằng rule/POS, có dependency fallback.
- Controlled concept vocabulary và alias.
- Exact match, embedding top-k và expert review.
- OOV/UNMAPPED policy.
- `concept_id`, `confidence`, `needs_review`.
- Gold standard và evaluation.

### Tùy chọn

- Intensity.
- `desired_direction` theo perspective.
- Suy luận tốt/xấu.
- Tô màu node theo góc nhìn tác nhân.
- LLM làm bộ chuẩn hóa chính.

## 16. Kết luận

Toàn bộ bước chuẩn hóa gồm hai bài toán liên tiếp:

```text
Factor Mention
→ Concept Candidate + State
→ Controlled Concept + State
```

Thiết kế tối ưu cho phạm vi luận văn là:

```text
Concept = nội dung trung tính và có concept_id ổn định
State   = CHANGE hoặc CONDITION, tách khỏi concept
Relation = quan hệ nhân quả đã trích xuất ở bước trước
```

Các nguyên tắc quan trọng nhất:

1. Không tạo concept chứa state.
2. Không đồng nhất `INCREASE` hoặc `DECREASE` với tốt hoặc xấu.
3. Không coi mọi state là chiều thay đổi; phải phân biệt CHANGE và CONDITION.
4. Không phụ thuộc hoàn toàn vào dependency parsing.
5. Ưu tiên under-merging hơn over-merging.
6. Không ép ánh xạ khi concept không đủ tương đồng.
7. Giữ lại `original_text`, confidence và trạng thái cần review.
8. Xây dựng gold standard và baseline để chứng minh hiệu quả.
9. Chỉ bổ sung `desired_direction` khi cần diễn giải theo perspective.

Phương án này vừa đủ chặt chẽ về ngữ nghĩa, vừa khả thi cho luận văn thạc sĩ và vẫn cho phép mở rộng về sau.
