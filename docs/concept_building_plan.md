# Kế hoạch xây dựng Controlled Concept Vocabulary

## 1. Mục tiêu

Controlled concept vocabulary không nên được tạo hoàn toàn tự động bằng embedding hoặc mô hình ngôn ngữ. Vocabulary cần được xây dựng từ các `concept_candidate` đã trích xuất trên corpus, sau đó được con người rà soát và chuẩn hóa.

Luồng tổng quát:

```text
Toàn bộ factor trong corpus
    ↓
Tách State và Concept Candidate
    ↓
Thống kê và gom nhóm candidate gần nghĩa
    ↓
Chuyên gia quyết định concept chuẩn và alias
    ↓
Controlled Concept Vocabulary
```

Vocabulary là tài nguyên có kiểm soát phục vụ ánh xạ các cách diễn đạt khác nhau về một `concept_id` ổn định. Nó không phải là danh sách từ đồng nghĩa được sinh tự động.

## 2. Thu thập Concept Candidate Inventory

Chạy bước normalization hiện tại trên toàn bộ causal factor để thu thập:

```text
original_text
concept_candidate
state
nguồn tài liệu
câu chứa factor
tần suất xuất hiện
```

Ví dụ:

| concept_candidate | Tần suất | Ví dụ |
|---|---:|---|
| chất lượng sản phẩm | 38 | nâng cao chất lượng sản phẩm |
| chất lượng nông sản | 21 | chất lượng nông sản thấp |
| chất lượng đầu ra | 7 | cải thiện chất lượng đầu ra |
| vốn | 42 | thiếu vốn |
| nguồn vốn | 18 | nguồn vốn hạn chế |
| kinh phí | 11 | không có đủ kinh phí |

Ở bước này chỉ loại các trường hợp trùng do định dạng hoặc chính tả đã được xác nhận. Chưa coi các candidate gần nghĩa là cùng một concept.

## 3. Xác định nguyên tắc tạo concept

Trước khi gom nhóm, cần thống nhất phạm vi miền và độ chi tiết của vocabulary.

Một concept chuẩn phải:

- Trung tính và không chứa state.
- Có ý nghĩa độc lập, ổn định.
- Phù hợp với phạm vi nghiên cứu.
- Không quá rộng đến mức gộp các hiện tượng khác nhau.
- Không quá hẹp hoặc phụ thuộc vào một câu văn cụ thể.

Ví dụ:

```text
chi phí tăng
→ concept: Chi phí
→ state: INCREASE
```

Không tạo các concept riêng như:

```text
C_COST_INCREASE = Chi phí tăng
C_HIGH_COST     = Chi phí cao
C_LOW_COST      = Chi phí thấp
```

Các biểu đạt trên phải dùng cùng concept `Chi phí`; `INCREASE`, `HIGH` và `LOW` được lưu trong `State`.

## 4. Gom nhóm candidate gần nghĩa

### 4.1. Gom nhóm chắc chắn bằng rule

Gom các biến thể chỉ khác định dạng:

```text
nguồn_vốn
nguồn vốn
Nguồn vốn
→ nguồn vốn
```

Có thể chuẩn hóa thêm các biến thể viết tắt hoặc chính tả đã được xác nhận:

```text
chi phí SX
chi phí sản xuất
→ chi phí sản xuất
```

### 4.2. Dùng embedding để đề xuất

Embedding chỉ tạo danh sách ứng viên gần nghĩa, không tự quyết định alias.

Ví dụ:

```text
Candidate: chất lượng nông sản

Gợi ý:
1. Chất lượng sản phẩm nông nghiệp — 0.91
2. Chất lượng đầu ra — 0.84
3. Năng suất nông nghiệp — 0.68
```

Người duyệt quyết định:

- Cùng concept: thêm làm alias.
- Liên quan nhưng khác nghĩa: giữ thành concept riêng.
- Chưa chắc chắn: để trạng thái `pending`.
- Candidate bị nhiễu: loại hoặc sửa lại bước extraction.

Không tự động đưa mọi candidate trong cùng embedding cluster vào một concept.

## 5. Tạo concept chuẩn và alias

Ví dụ sau khi rà soát:

```text
Concept ID:
C_PRODUCT_QUALITY

Preferred label:
Chất lượng sản phẩm nông nghiệp

Approved aliases:
- chất lượng sản phẩm
- chất lượng nông sản
```

`chất lượng đầu ra` chưa chắc đồng nghĩa trong mọi bối cảnh, vì vậy có thể được giữ ở trạng thái chờ duyệt:

```text
Pending review:
- chất lượng đầu ra
```

Ví dụ khác:

```text
Concept ID:
C_CAPITAL

Preferred label:
Vốn

Aliases:
- nguồn vốn
- kinh phí
```

Chỉ thêm `kinh phí` làm alias nếu trong phạm vi nghiên cứu, `kinh phí` và `vốn` được phép quy về cùng mức trừu tượng. Nếu cần phân biệt ngân sách và vốn đầu tư thì phải tạo concept riêng.

## 6. Sử dụng Concept ID ổn định

Nên sử dụng ID không phụ thuộc hoàn toàn vào preferred label:

```text
C_0001
C_0002
C_0003
```

Hoặc sử dụng ID có nghĩa nhưng vẫn ổn định:

```text
C_CAPITAL
C_PRODUCT_QUALITY
C_PRODUCTION_COST
```

ID không thay đổi khi preferred label được chỉnh sửa.

Ví dụ:

```text
C_PRODUCT_QUALITY → Chất lượng sản phẩm
```

Sau này có thể đổi nhãn thành:

```text
C_PRODUCT_QUALITY → Chất lượng sản phẩm nông nghiệp
```

Node trong causal graph vẫn giữ nguyên `concept_id`.

## 7. Cấu trúc Vocabulary Workbook

Vocabulary được lưu trong một workbook Excel gồm ít nhất hai sheet.

### 7.1. Sheet `concepts`

| concept_id | preferred_label |
|---|---|
| C_CAPITAL | Vốn |
| C_PRODUCT_QUALITY | Chất lượng sản phẩm nông nghiệp |
| C_PRODUCTION_COST | Chi phí sản xuất |

### 7.2. Sheet `aliases`

| concept_id | alias |
|---|---|
| C_CAPITAL | nguồn vốn |
| C_CAPITAL | kinh phí |
| C_PRODUCT_QUALITY | chất lượng sản phẩm |
| C_PRODUCT_QUALITY | chất lượng nông sản |
| C_PRODUCTION_COST | chi phí sản xuất nông nghiệp |

Nên lưu alias trong sheet riêng thay vì đặt nhiều alias trong một ô. Cách này giúp theo dõi trạng thái duyệt, nguồn dữ liệu, người duyệt và bằng chứng cho quyết định.

Trong giai đoạn xây dựng, sheet `aliases` có thể được mở rộng:

| concept_id | alias | status | reviewer | evidence |
|---|---|---|---|---|
| C_CAPITAL | nguồn vốn | approved | A | 18 mentions |
| C_CAPITAL | kinh phí | pending |  | cần kiểm tra ngữ cảnh |
| C_PRODUCT_QUALITY | chất lượng nông sản | approved | B | 21 mentions |

Pipeline production chỉ sử dụng các alias có `status = approved`.

## 8. Quy trình duyệt

Mỗi nhóm candidate được đánh giá bằng các câu hỏi:

1. Các candidate có chỉ cùng một thực thể, thuộc tính, hoạt động hoặc hiện tượng không?
2. Chúng có chỉ khác nhau về state hoặc mức độ không?
3. Chúng có quan hệ cha–con thay vì quan hệ đồng nghĩa không?
4. Chúng có chỉ đồng nghĩa trong một ngữ cảnh cụ thể không?
5. Việc gộp có làm mất thông tin quan trọng của causal graph không?

Ví dụ:

```text
vốn
vốn đầu tư
vốn lưu động
```

Không nên mặc định gộp cả ba. Nếu phạm vi nghiên cứu cần phân biệt, có thể biểu diễn:

```text
C_CAPITAL
├── C_INVESTMENT_CAPITAL
└── C_WORKING_CAPITAL
```

Nếu chưa triển khai hierarchy, vẫn nên giữ các concept riêng để tránh over-merging.

Đối với một phần dữ liệu quan trọng, nên có ít nhất hai người duyệt độc lập và một bước thống nhất khi có bất đồng.

## 9. Thứ tự ưu tiên duyệt candidate

Không cần duyệt tất cả candidate cùng lúc. Ưu tiên:

1. Candidate xuất hiện nhiều nhất.
2. Candidate tham gia nhiều quan hệ nhân quả.
3. Candidate có nhiều biến thể gần nghĩa.
4. Candidate tạo node quan trọng trong graph.
5. Candidate có mức độ nhập nhằng cao.

Chiến lược lặp:

```text
Vòng 1: Duyệt top candidate theo tần suất
    ↓
Tạo vocabulary seed
    ↓
Vòng 2: Map toàn bộ corpus
    ↓
Thu thập UNMAPPED và vùng xám
    ↓
Vòng 3: Duyệt candidate quan trọng còn lại
    ↓
Bổ sung concept hoặc alias
    ↓
Lặp lại đến khi đạt coverage yêu cầu
```

## 10. Chính sách bảo thủ

Ưu tiên under-merging hơn over-merging:

- Chưa chắc chắn thì giữ hai concept riêng.
- Không thêm alias chỉ dựa trên cosine similarity.
- Không ép candidate vào concept gần nhất.
- Candidate chưa đủ bằng chứng được giữ là `UNMAPPED` hoặc `pending`.
- Giữ lại câu gốc và nguồn dữ liệu để phục vụ truy vết.

Embedding và clustering hỗ trợ giảm công sức duyệt; quyết định cuối cùng thuộc về quy tắc miền và người duyệt.

## 11. Tiêu chí vocabulary đủ dùng

Vocabulary seed có thể được đưa vào thử nghiệm khi:

- Các candidate xuất hiện thường xuyên đã được duyệt.
- Alias chỉ chứa các trường hợp đã xác nhận.
- Candidate chưa chắc chắn vẫn được giữ là `UNMAPPED`.
- Tỷ lệ mapping đúng được kiểm tra trên một mẫu thủ công.
- Mỗi concept có ví dụ hoặc bằng chứng cho quyết định gộp alias.
- Không còn preferred label hoặc alias chứa state.
- Các thay đổi vocabulary được quản lý phiên bản.

Không cần chờ vocabulary bao phủ 100% corpus mới bắt đầu đánh giá.

## 12. Lộ trình triển khai

### Giai đoạn 1 — Tạo inventory

1. Chạy normalization trên toàn bộ factor.
2. Xuất `concept_candidate` kèm tần suất, state, câu ví dụ và nguồn.
3. Loại trùng bề mặt.
4. Phát hiện các candidate có khả năng là lỗi extraction.

### Giai đoạn 2 — Tạo vocabulary seed

1. Chọn candidate ưu tiên theo tần suất và vai trò trong graph.
2. Dùng embedding tạo nhóm gợi ý.
3. Duyệt thủ công từng nhóm.
4. Chọn preferred label và cấp `concept_id` ổn định.
5. Ghi alias đã duyệt vào workbook.

### Giai đoạn 3 — Ánh xạ và mở rộng

1. Chạy exact preferred-label và alias matching.
2. Chạy embedding top-k cho candidate chưa map được.
3. Tự động nhận kết quả có độ tin cậy cao theo ngưỡng đã hiệu chỉnh.
4. Đưa vùng xám vào hàng đợi review.
5. Giữ candidate điểm thấp là `UNMAPPED`.
6. Cập nhật vocabulary sau mỗi vòng duyệt.

### Giai đoạn 4 — Đánh giá

1. Xây dựng gold-standard sample.
2. Đánh giá preferred-label và alias mapping.
3. Đánh giá top-1 accuracy và top-k recall của embedding.
4. Đo tỷ lệ auto-mapped, `needs_review` và `UNMAPPED`.
5. Phân tích over-merging và under-merging.
6. Hiệu chỉnh ngưỡng rồi khóa phiên bản vocabulary dùng trong thí nghiệm.

## 13. Kết quả đầu ra

Quá trình xây dựng cần tạo ra ít nhất các artefact sau:

```text
concept_candidate_inventory.xlsx
controlled_concept_vocabulary.xlsx
concept_review_queue.xlsx
concept_mapping_evaluation.xlsx
```

Trong đó:

- `concept_candidate_inventory.xlsx`: toàn bộ candidate, tần suất và evidence.
- `controlled_concept_vocabulary.xlsx`: concept và alias đã duyệt.
- `concept_review_queue.xlsx`: candidate chưa chắc chắn hoặc chưa map được.
- `concept_mapping_evaluation.xlsx`: gold labels, kết quả mapping và metric.

## 14. Bước tiếp theo

Bước triển khai gần nhất là tạo script xuất toàn bộ `concept_candidate` thành `concept_candidate_inventory.xlsx`, kèm theo:

```text
candidate chuẩn hóa
tần suất
original factor
state
câu chứa factor
nguồn dữ liệu
```

Inventory này là đầu vào cho vòng duyệt đầu tiên và là nền tảng để xây dựng controlled concept vocabulary từ dữ liệu thực tế.
