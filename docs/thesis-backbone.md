# Khung nền tảng của luận văn

## 1. Định vị đề tài

**Tên đề tài:** *Phân tích các yếu tố chi phối quyết định ứng dụng công cụ số
trong sản xuất lúa gạo bằng khai phá dữ liệu và đồ thị nhân quả.*

Trọng tâm của luận văn là **nhận diện, hệ thống hóa và phân tích các yếu tố chi
phối quyết định ứng dụng công cụ số trong sản xuất lúa gạo**. Các mô hình xử lý
ngôn ngữ chỉ là phương tiện chuyển văn bản phi cấu trúc thành dữ liệu có cấu
trúc phục vụ việc xây dựng và phân tích đồ thị.

Đồ thị trong luận văn biểu diễn các quan hệ nhân quả **được phát biểu trong tập
văn bản**; nó không tự chứng minh quan hệ nhân quả ngoài thực tế.

## 2. Bài toán và mục tiêu

Thông tin về ứng dụng công cụ số trong nông nghiệp được trình bày phân tán trong
các văn bản tiếng Việt, với cách diễn đạt đa dạng và nhiều câu phức chứa đồng
thời nhiều yếu tố hoặc hệ quả. Nếu dùng trực tiếp toàn bộ các cụm từ bề mặt làm
nút, những cách diễn đạt gần nghĩa có thể tạo thành nhiều nút riêng biệt, khiến
đồ thị bị phân mảnh và khó quan sát ở mức khái quát.

Mục tiêu chung của luận văn là khai phá dữ liệu văn bản tiếng Việt để nhận diện
các yếu tố, trạng thái của yếu tố và quan hệ tác động giữa chúng; sau đó gom
nhóm các `concept_candidate` tương đồng về ngữ nghĩa để hình thành các `concept`
ở mức khái quát, đồng thời bảo toàn toàn bộ dữ liệu thành phần và nguồn gốc của
chúng. Các quan hệ được tổ chức thành đồ thị nhằm phục vụ phân tích quyết định
ứng dụng công cụ số trong sản xuất lúa gạo.

Các câu hỏi kỹ thuật chính:

1. Làm thế nào tách câu phức thành các câu đơn mà không làm mất thông tin hoặc
   thay đổi chiều nhân quả?
2. Làm thế nào trích xuất nhất quán cấu trúc
   `subject – predicate – object` từ mỗi câu đơn?
3. Làm thế nào phân rã subject và object thành `concept_candidate` và `state`,
   đồng thời xử lý đúng phủ định và mức độ?
4. Làm thế nào tự động gom nhóm các `concept_candidate` tương đồng để hình thành
   các `concept`, hợp nhất các quan hệ liên quan và tổ chức chúng thành đồ thị có
   khả năng truy vết?
5. Làm thế nào phân tích các yếu tố trực tiếp và gián tiếp chi phối quyết định
   ứng dụng công cụ số từ đồ thị kết quả?

## 3. Phạm vi dữ liệu

- Ngôn ngữ: tiếng Việt.
- Dạng dữ liệu: bài báo và văn bản trực tuyến phi cấu trúc.
- Miền thu thập: chuyển đổi số trong nông nghiệp.
- Trọng tâm phân tích: các yếu tố liên quan đến quyết định ứng dụng công cụ số
  trong sản xuất lúa gạo.
- Nguồn đang được dự án hỗ trợ thu thập: VnExpress và Báo Nông nghiệp và Môi
  trường.

Không mặc định mọi nội dung về chuyển đổi số nông nghiệp đều thuộc phạm vi phân
tích. Corpus cuối cùng cần có tiêu chí chọn nguồn, thời gian, mức độ liên quan
và quy trình loại nhiễu rõ ràng.

## 4. Biểu diễn tri thức

Mỗi phát biểu nhân quả nguyên tử sau bước phân rã `concept/state` được biểu diễn
ở mức trung gian dưới dạng:

```text
(source_concept_candidate, source_state)
        ── predicate ──>
(target_concept_candidate, target_state)
```

Trong đầu ra trung gian:

- `subject` tương ứng với phía nguồn/nguyên nhân;
- `object` tương ứng với phía đích/kết quả;
- `predicate` biểu diễn quan hệ giữa hai phía;
- `concept_candidate` là phần yếu tố được trích xuất trực tiếp từ factor trong
  văn bản;
- `state` là trạng thái, xu hướng, mức độ hoặc thuộc tính của
  `concept_candidate`.

`Subject/object` ở đây là vai trò ngữ nghĩa sau khi câu đã được chuẩn hóa theo
chiều nguyên nhân → kết quả, không chỉ là chủ ngữ/tân ngữ ngữ pháp của câu gốc.

Ví dụ:

```text
Thiếu kỹ năng số khiến nông dân khó tiếp cận công nghệ.

source_concept_candidate = kỹ năng số
source_state             = LACK
predicate                = khiến
target_concept_candidate = tiếp cận công nghệ
target_state             = DIFFICULT
```

Sau bước gom nhóm ngữ nghĩa, mỗi `concept_candidate` được gắn với một
`concept_id` tương ứng với nhóm mà nó thuộc về:

```text
concept_candidate
        ↓ semantic clustering
concept_id
```

`Concept` không thay thế hoặc xóa `concept_candidate`. Nó là lớp khái quát được
hình thành từ một nhóm các `concept_candidate` tương đồng. Mỗi quan hệ vẫn giữ
nguyên `concept_candidate`, `state`, `predicate`, câu nguồn và tài liệu nguồn để
phục vụ truy vết và xem chi tiết.

Biểu diễn quan hệ sau khi gắn nhóm concept có dạng:

```text
(source_concept_id, source_concept_candidate, source_state)
        ── predicate ──>
(target_concept_id, target_concept_candidate, target_state)
```

## 5. Pipeline kỹ thuật

```text
Văn bản tiếng Việt
        ↓
Thu thập, làm sạch, phân đoạn và lọc nội dung liên quan
        ↓
[1] Tách câu phức thành các câu đơn
        ↓
[2] Trích xuất subject – predicate – object
        ↓
[3] Phân rã concept_candidate/state cho subject và object
        ↓
[4] Gom nhóm ngữ nghĩa các concept_candidate
        ↓
[5] Hợp nhất các quan hệ liên quan và xây dựng đồ thị
        ↓
[6] Phân tích các yếu tố chi phối
```

Pipeline tách riêng các tác vụ sinh văn bản, trích xuất quan hệ, gán nhãn chuỗi,
gom nhóm ngữ nghĩa và xây dựng đồ thị. Mỗi bước sử dụng một phương pháp chuyên
biệt thay vì yêu cầu một LLM lớn thực hiện đồng thời toàn bộ quá trình.

### 5.1. Tách câu phức thành câu đơn

**Phương án:** fine-tune BARTpho hoặc ViT5 cho tác vụ sinh câu đơn.

**Dữ liệu huấn luyện:** sử dụng knowledge distillation từ LLM:

1. Dùng prompt đã kiểm thử để LLM tách các câu phức trong corpus.
2. Tạo cặp huấn luyện `câu gốc → danh sách câu đơn`.
3. Con người rà soát mẫu, loại hoặc sửa các kết quả không trung thành.
4. Fine-tune và đánh giá mô hình tiếng Việt trên dữ liệu đã kiểm soát.

Đầu ra phải bảo toàn nội dung định lượng, tham chiếu, mức độ và chiều quan hệ;
không được biến hệ quả gián tiếp thành tác động trực tiếp.

### 5.2. Trích xuất cấu trúc S–P–O

**Phương án:** fine-tune toàn bộ mREBEL trên tập quan hệ nhân quả được xây dựng
theo schema của luận văn.

Mô hình nhận câu đơn và sinh:

```text
subject – predicate – object
```

Các loại quan hệ Wikidata nguyên bản của mREBEL không được xem là schema đầu ra
của luận văn. Tập fine-tune phải chứa câu đơn cùng subject, predicate và object
được gán nhãn theo miền nghiên cứu. Hiệu quả của mREBEL trên dữ liệu này chỉ
được khẳng định sau thực nghiệm.

### 5.3. Phân rã concept candidate và state

**Phương án:** PhoBERT làm encoder, kết hợp một lớp token classification theo
BIO tagging.

Mô hình được áp dụng riêng lên `subject.text` và `object.text` để xác định các
span:

```text
B-CONCEPT, I-CONCEPT
B-STATE,   I-STATE
O
```

Span `CONCEPT` tạo ra `concept_candidate`; span `STATE` tạo ra `state` của factor
trong phát biểu cụ thể.

State phải phân biệt tối thiểu trạng thái động và điều kiện tĩnh. Phủ định cần
được giữ riêng; chẳng hạn `không tăng` không được tự động đổi thành `giảm`.

GLiREL không được sử dụng ở bước này vì đây là tác vụ gán nhãn token, không
phải phân loại quan hệ giữa các thực thể.

### 5.4. Gom nhóm ngữ nghĩa và hình thành concept

Phương pháp không ánh xạ `concept_candidate` vào một controlled concept
vocabulary được xây dựng trước. Thay vào đó, các `concept_candidate` được hình
thành từ corpus và được gom nhóm tự động dựa trên mức độ tương đồng ngữ nghĩa
của chính chuỗi `concept_candidate`.

Quy trình khái quát:

1. Thu thập các lần xuất hiện của `concept_candidate` từ subject và object.
2. Chuẩn hóa hình thức văn bản ở mức không làm thay đổi nội dung.
3. Tạo biểu diễn embedding cho từng `concept_candidate`.
4. Gom nhóm các biểu diễn tương đồng bằng thuật toán clustering.
5. Gán một `concept_id` cho mỗi nhóm.
6. Chọn một nhãn đại diện cho nhóm theo quy tắc được xác định trong thực nghiệm.
7. Giữ nguyên toàn bộ `concept_candidate` thành phần và liên kết của chúng với
   factor, relation, câu và tài liệu nguồn.

Đầu vào của bước gom nhóm chỉ là nội dung ngữ nghĩa của `concept_candidate`.
`State`, `predicate`, concept ở đầu còn lại và câu nguồn không tham gia trực tiếp
vào biểu diễn dùng để hình thành node. Những thông tin này được bảo toàn trong
các quan hệ thành phần để người dùng có thể xem chi tiết khi truy xuất node hoặc
cạnh trên đồ thị.

Mỗi concept được hình thành theo hướng data-driven:

```text
Concept
├── concept_id
├── representative_label
└── member_concept_candidates
```

Một `concept_candidate` không bị thay thế sau khi được gắn vào concept. Trong
dữ liệu quan hệ, factor tiếp tục lưu cả `concept_candidate` và `concept_id`.

Phương pháp không bắt buộc mọi `concept_candidate` phải được gộp vào một nhóm
lớn. Những candidate không đủ tương đồng với các candidate khác có thể tạo thành
nhóm riêng. Cách này hạn chế việc ép các yếu tố không tương đồng vào cùng một
concept.

### 5.5. Hợp nhất quan hệ và xây dựng đồ thị

Sau khi source và target của mỗi quan hệ được gắn với `concept_id`, các quan hệ
có cùng cặp `source_concept_id` và `target_concept_id` được tập hợp để hình thành
một liên kết ở mức khái quát trên đồ thị.

Việc hợp nhất không xóa các quan hệ gốc. Mỗi cạnh tổng hợp giữ một danh sách
các quan hệ thành phần, trong đó mỗi quan hệ vẫn chứa:

```text
source_concept_candidate
source_state
predicate
target_concept_candidate
target_state
simple_sentence
original_sentence
document_id/source
```

Khi người dùng chọn một node, hệ thống có thể hiển thị các
`concept_candidate` thành phần của concept. Khi người dùng chọn một cạnh, hệ
thống có thể hiển thị các quan hệ thành phần và văn bản nguồn đã được tập hợp
trong cạnh đó.

## 6. Thiết kế đồ thị

### 6.1. Node

Mỗi node là một `concept` được hình thành tự động từ một nhóm các
`concept_candidate` tương đồng về ngữ nghĩa.

Node lưu tối thiểu:

```text
concept_id
representative_label
member_concept_candidates
```

Ví dụ:

```text
Concept: Năng lực số

member_concept_candidates:
- kỹ năng số
- năng lực số
- khả năng sử dụng công nghệ số
```

Nhãn đại diện chỉ phục vụ hiển thị và mô tả nhóm; nó không thay thế các
`concept_candidate` thành phần.

Không tạo node riêng cho từng tổ hợp `concept + state`, vì cách này làm phân
mảnh cùng một yếu tố thành nhiều nút. `State` vẫn thuộc từng lần xuất hiện của
factor trong một quan hệ cụ thể.

### 6.2. Edge

Mỗi cạnh có hướng từ source concept đến target concept. Một cạnh là lớp tổng hợp
của các quan hệ thành phần có cùng cặp `source_concept_id` và
`target_concept_id`.

Cạnh lưu tối thiểu một danh sách evidence, trong đó mỗi evidence chứa:

```text
source_concept_candidate
source_state
predicate
target_concept_candidate
target_state
simple_sentence
original_sentence
document_id/source
```

Không ghi đè một quan hệ thành phần bằng quan hệ khác. Các predicate, state và
câu nguồn khác nhau phải được bảo toàn để người dùng có thể xem chi tiết và để
luận văn có khả năng phân tích lỗi.

Số lượng quan hệ thành phần có thể được dùng như một thống kê về mức độ xuất
hiện trong corpus, nhưng không được đồng nhất trực tiếp với cường độ tác động
nhân quả trong thực tế.

### 6.3. Hai tầng biểu diễn

Đồ thị được tổ chức theo hai tầng:

```text
Tầng khái quát:
Concept ──> Concept

Tầng chi tiết:
concept_candidate + state + predicate + câu nguồn + tài liệu nguồn
```

Tầng khái quát hỗ trợ quan sát cấu trúc chung và phân tích các nhóm yếu tố. Tầng
chi tiết bảo toàn dữ liệu khai phá ban đầu và cho phép kiểm tra các phát biểu
thành phần của từng node hoặc cạnh.

## 7. Dữ liệu huấn luyện và đánh giá

Mỗi bước cần tập phát triển và tập đánh giá độc lập với dữ liệu dùng để điều
chỉnh mô hình, prompt hoặc cấu hình thuật toán.

| Bước | Dữ liệu cần có | Nội dung đánh giá chính |
|---|---|---|
| Tách câu | Câu phức và các câu đơn đã duyệt | Độ trung thành ngữ nghĩa, độ đầy đủ, đúng chiều nhân quả |
| Trích xuất S–P–O | Câu đơn và bộ ba được gán nhãn | Precision, Recall, F1 của subject, predicate và object |
| Concept/state | Factor được gán nhãn BIO | Precision, Recall, F1 theo span/nhãn; độ đúng của state và phủ định |
| Gom nhóm concept candidate | Các concept candidate và kết quả clustering | Độ nhất quán của nhóm trên mẫu đánh giá; lỗi gộp sai, lỗi tách sai và độ ổn định theo cấu hình |
| Hợp nhất quan hệ và đồ thị | Quan hệ đã gắn concept_id cùng nguồn gốc | Tính hợp lệ của node/cạnh, khả năng bảo toàn quan hệ thành phần và khả năng truy vết |
| Phân tích yếu tố | Đồ thị và tập bằng chứng | Tính hợp lý của yếu tố trực tiếp/gián tiếp, độ ổn định và khả năng kiểm chứng từ dữ liệu nguồn |

Việc đánh giá gom nhóm không đòi hỏi xây dựng trước một concept vocabulary bao
phủ toàn bộ corpus. Có thể đánh giá trên một mẫu các cluster, tập trung vào câu
hỏi liệu các `concept_candidate` trong cùng nhóm có đủ nhất quán để được trình
bày dưới cùng một node tổng hợp hay không.

LLM prompting có thể được dùng làm teacher và baseline. Chỉ tuyên bố mô hình
hoặc phương pháp chuyên biệt tốt hơn khi có cùng tập đánh giá, tiêu chí và số
liệu so sánh.

## 8. Các quyết định còn mở

Các điểm sau cần được giảng viên hướng dẫn xác nhận hoặc được chốt trong quá
trình thực nghiệm:

1. Node `Quyết định ứng dụng công cụ số` là node đích cố định hay được hình
   thành bằng cùng quy trình gom nhóm như các concept khác.
2. Tiêu chí phân biệt nguyên nhân với điều kiện hoặc bối cảnh nền.
3. Schema state chính thức, đặc biệt đối với phủ định và mức độ.
4. Quy tắc gán nhãn predicate và mức độ chuẩn hóa predicate.
5. Mô hình embedding dùng để biểu diễn `concept_candidate`.
6. Thuật toán clustering và cách lựa chọn số nhóm hoặc ngưỡng gom nhóm.
7. Quy tắc chọn `representative_label` cho mỗi concept.
8. Chính sách xử lý các cạnh có cùng cặp concept nhưng chứa predicate hoặc state
   khác nhau, đặc biệt khi các bằng chứng thể hiện chiều tác động không thống
   nhất.
9. Quy mô dữ liệu huấn luyện, quy trình gán nhãn và cách xử lý bất đồng.
10. Baseline và bộ chỉ số đánh giá chính thức cho từng bước.
11. Phương pháp phân tích và xếp hạng các yếu tố chi phối trên đồ thị.

## 9. Nguyên tắc viết báo cáo

- Phần “Đặt vấn đề” và “Mục tiêu nghiên cứu” phải tập trung vào bài toán phân
  tích các yếu tố chi phối; không đặt tên mô hình làm trọng tâm.
- BARTpho/ViT5, mREBEL, PhoBERT, knowledge distillation, semantic embedding và
  clustering thuộc chương phương pháp.
- Pipeline trên là phương án kỹ thuật đã lựa chọn, chưa phải kết quả thực
  nghiệm.
- Không tuyên bố mô hình hoặc phương pháp đạt hiệu quả cao, vượt baseline hoặc
  có khả năng khái quát khi chưa có số liệu.
- Không mô tả bước gom nhóm như ánh xạ vào một controlled concept vocabulary
  hoặc ontology được xác định trước.
- Không tuyên bố các `concept_candidate` trong cùng cluster hoàn toàn đồng nghĩa;
  cluster là lớp khái quát phục vụ tổ chức và trực quan hóa dữ liệu.
- Không gọi đây là đồ thị chứng minh nhân quả; đây là đồ thị tổ chức các quan
  hệ nhân quả được khai phá từ văn bản.
- Mọi concept, node và cạnh phải có khả năng truy vết về
  `concept_candidate`, factor, quan hệ thành phần, câu đơn, câu gốc và tài liệu
  nguồn.
