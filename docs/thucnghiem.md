# ĐỀ XUẤT MỤC LỤC CHƯƠNG 3 – THỰC NGHIỆM

## Định hướng tổ chức chương

Chương 3 trình bày những gì đã được **triển khai và chạy thực tế** trên dữ
liệu, đối chiếu với phương án đã đề xuất ở Chương 2. Chương 3 không lặp lại
phần mô tả phương pháp; mỗi mục chỉ nêu: cấu hình/công cụ đã dùng, dữ liệu đã
chạy, kết quả (định lượng và định tính), ví dụ minh họa và lỗi quan sát được.

Ba câu hỏi chương này phải trả lời được:

1. Với dữ liệu và cấu hình hiện có, từng bước của pipeline hoạt động ra sao,
   ở quy mô nào?
2. Kết quả (câu đơn, quan hệ, concept, đồ thị) có đáng tin để dùng cho bước
   phân tích tiếp theo hay không, và giới hạn ở đâu?
3. Trong các bước còn dùng luật thủ công, đâu là bằng chứng cho thấy đóng góp
   của luận văn không chỉ là một pipeline heuristic dựa trên VnCoreNLP?

> **Giả định phạm vi cho phiên bản mục lục này:** Hai bước sau được giả định
> đã hoàn thành, thay thế cho phần đang dùng LLM prompting trực tiếp:
>
> 1. Mô hình student **ViT5** cho tách câu phức, huấn luyện qua chắt lọc tri
>    thức từ LLM teacher (Mục 2.3).
> 2. **Thuật toán clustering tự động** cho bước gom nhóm concept candidate,
>    thay cho quy trình bán tự động dựa trên hàng đợi rà soát thủ công
>    (Mục 2.6).
>
> Mô-đun phân tích yếu tố trực tiếp/gián tiếp trên đồ thị (Mục 2.8) **không
> đưa vào phạm vi chương này**.
>
> Trích xuất quan hệ S–P–O và phân rã concept candidate/state **vẫn đang
> dùng luật** dựa trên dependency tree và từ điển (chưa fine-tune mREBEL và
> PhoBERT–BIO); nội dung các mục liên quan vẫn phản ánh đúng thực tế đó, không
> giả định đã có mô hình fine-tune cho hai bước này.

## Phạm vi và quy mô thực nghiệm hiện tại

Bảng này nên mở đầu Chương 3 để đặt đúng kỳ vọng cho người đọc:

| Thành phần | Trạng thái được trình bày trong chương |
|---|---|
| Thu thập liên kết bài viết | Đã tự động hóa cho VnExpress và Báo Nông nghiệp và Môi trường; đã thu được danh sách liên kết ở quy mô hàng nghìn |
| Tải và làm sạch văn bản đầy đủ | Xử lý ở quy mô thí điểm, chưa tải và chạy toàn bộ danh sách liên kết đã thu thập |
| Tách câu phức | Giả định đã fine-tune xong ViT5 qua chắt lọc tri thức từ LLM teacher; báo cáo kết quả trên tập test độc lập |
| Trích xuất S–P–O | Vẫn dùng luật dựa trên dependency tree (VnCoreNLP) và từ điển trigger nhân quả; chưa fine-tune mREBEL |
| Phân rã concept candidate/state | Vẫn dùng luật/từ điển trạng thái; chưa fine-tune PhoBERT–BIO |
| Gom nhóm concept candidate | Giả định đã có thuật toán clustering tự động; báo cáo cấu hình cuối và thống kê cụm |
| Xây dựng đồ thị | Đã có, chạy được và xuất ra file trực quan hóa |
| Phân tích yếu tố trực tiếp/gián tiếp | Không trình bày trong chương này |
| Đánh giá định lượng (P/R/F1...) | Có cho các bước đã giả định hoàn thành (ViT5, clustering); chưa có bộ test độc lập chính thức cho hai bước còn lại |

Mục này cần nêu rõ đây là **kết quả ở giai đoạn thí điểm (pilot)** về quy mô
dữ liệu, dùng để kiểm chứng tính khả thi của kiến trúc, không phải kết quả
cuối cùng trên toàn bộ corpus.

---

# CHƯƠNG 3. THỰC NGHIỆM

## 3.1. Môi trường và công cụ thực nghiệm

- Cấu hình phần cứng, phần mềm, phiên bản Python.
- Danh sách thư viện/công cụ đã dùng trong thực tế: VnCoreNLP (qua
  `py_vncorenlp`), ViT5 cho tách câu, mô hình embedding câu tiếng Việt và
  thuật toán clustering cho bước gom nhóm, LLM teacher dùng để sinh dữ liệu
  distillation, `networkx` cho đồ thị.
- Bảng đối chiếu giữa từng bước trong Chương 2 và trạng thái triển khai thực
  tế tại thời điểm viết luận văn (bước nào đã có mô hình/thuật toán như
  phương án đề xuất, bước nào vẫn dùng luật tạm thời).
- Cách quản lý khóa API và cấu hình môi trường (không đưa khóa bí mật vào mã
  nguồn hoặc báo cáo).

## 3.2. Xây dựng corpus thực nghiệm

- Quy trình thu thập liên kết tự động theo nguồn (VnExpress, Báo Nông nghiệp
  và Môi trường): số liên kết thô thu được, số liên kết duy nhất sau khi
  chuẩn hóa URL và loại trùng.
- Quy mô văn bản đã tải và làm sạch để chạy pipeline trích xuất (tập thí
  điểm), lý do giới hạn quy mô ở giai đoạn này.
- Kết quả phân đoạn và lọc mức độ liên quan: số đoạn (chunk) sinh ra, số đoạn
  được giữ lại sau lọc, tỷ lệ loại bỏ.
- Ví dụ một đoạn bị loại và một đoạn được giữ, kèm lý do.

**Bảng 3.1:** Thống kê corpus thực nghiệm (liên kết thu thập, văn bản đã xử
lý, số đoạn trước/sau lọc).

## 3.3. Thực nghiệm phân rã câu phức bằng mô hình student ViT5

- Dữ liệu distillation đã dùng để fine-tune: số cặp câu phức → danh sách câu
  đơn được LLM teacher sinh ra, tỷ lệ được giữ lại sau rà soát và hiệu chỉnh.
- Cấu hình fine-tune: checkpoint khởi tạo, cách chia train/dev/test, tiêu chí
  chọn checkpoint trên tập dev.
- Kết quả định lượng trên tập test độc lập theo các tiêu chí đã đặt ở
  Mục 2.9: độ trung thành ngữ nghĩa, độ đầy đủ thông tin, độ chính xác về
  phủ định/định lượng/tham chiếu, độ chính xác về chiều nguyên nhân–kết quả.
- So sánh kết quả của ViT5 (student) với LLM teacher trên cùng tập test, để
  đánh giá mức độ giữ được chất lượng sau chắt lọc tri thức.
- Ví dụ câu tách đúng và một số trường hợp ViT5 tách sai hoặc mất thông tin,
  phân loại theo dạng lỗi.

**Bảng 3.2:** Kết quả tách câu của ViT5 so với LLM teacher trên tập test.

## 3.4. Thực nghiệm trích xuất quan hệ S–P–O bằng luật dựa trên dependency tree

- Vì mREBEL chưa được fine-tune, mục này báo cáo kết quả của bộ trích xuất
  quan hệ hiện tại: kết hợp cây phụ thuộc cú pháp (VnCoreNLP) với từ điển
  trigger nhân quả và tập luật cấu trúc câu, chạy trên đầu ra câu đơn của
  ViT5 ở Mục 3.3.
- Liệt kê các mẫu cấu trúc (pattern) đã cài đặt và tần suất mỗi mẫu khớp trên
  corpus thí điểm.
- Thống kê số quan hệ trích xuất được, tỷ lệ quan hệ có đủ cả nguồn và đích,
  tỷ lệ câu không khớp mẫu nào.
- Phân tích lỗi điển hình: sai chiều nguyên nhân–kết quả, thiếu vế do cắt mệnh
  đề phụ, trigger bị nhận diện sai ngữ cảnh.
- Đối chiếu định tính một mẫu nhỏ giữa kết quả luật và kết quả LLM prompting
  trên cùng một số câu, làm cơ sở thảo luận đóng góp ở Mục 3.8.

**Bảng 3.3:** Thống kê quan hệ trích xuất theo từng mẫu cấu trúc.
**Bảng 3.4:** Ví dụ đối chiếu kết quả luật và kết quả LLM trên cùng một câu.

## 3.5. Thực nghiệm phân rã concept candidate và state

- Vì PhoBERT–BIO chưa được fine-tune, mục này báo cáo kết quả của bước phân
  rã dựa trên từ điển trạng thái và luật xử lý phủ định/mức độ hiện có, chạy
  trên subject/object của các quan hệ ở Mục 3.4.
- Thống kê số `concept_candidate` và `state` tách được.
- Ví dụ minh họa: trường hợp phủ định được giữ đúng, trường hợp mức độ/số
  lượng được giữ đúng, và một số trường hợp còn sai (ranh giới span, thiếu
  state, gán nhầm concept).
- Ghi nhận các trường hợp chưa được từ điển trạng thái hiện tại bao phủ.

**Bảng 3.5:** Thống kê concept candidate và state tách được.

## 3.6. Thực nghiệm gom nhóm ngữ nghĩa concept candidate bằng thuật toán clustering tự động

- Cấu hình cuối cùng: mô hình embedding dùng cho `concept_candidate`, thuật
  toán clustering đã chọn, ngưỡng/số cụm hoặc tham số tương ứng.
- Thống kê cụm: số `concept_candidate` duy nhất sau chuẩn hóa đưa vào
  clustering, số cụm sinh ra, phân bố kích thước cụm, tỷ lệ cụm singleton.
- Đánh giá trên một mẫu cụm theo tiêu chí đã đặt ở Mục 2.9: mức nhất quán
  ngữ nghĩa trong cụm, lỗi gộp sai, lỗi tách sai.
- Phân tích độ nhạy và tính ổn định của cụm khi thay đổi ngưỡng, số cụm hoặc
  seed.
- Quy tắc chọn `representative_label` đã áp dụng và một số ví dụ.
- Ví dụ cụm tốt, cụm gộp nhầm, cụm tách nhầm.

**Bảng 3.6:** Cấu hình clustering cuối cùng và thống kê cụm.
**Bảng 3.7:** Kết quả đánh giá thủ công trên mẫu cụm (gộp sai/tách sai/nhất
quán).

## 3.7. Xây dựng và trực quan hóa đồ thị

- Thống kê đồ thị thu được từ dữ liệu thí điểm: số node (concept), số edge,
  số quan hệ thành phần được gộp vào các edge, mật độ đồ thị.
- Một số ví dụ node có nhiều `concept_candidate` thành viên và một số node
  chỉ có một candidate (singleton).
- Một số ví dụ edge có nhiều quan hệ thành phần với state/predicate khác
  nhau, minh họa khả năng truy vết về câu và tài liệu nguồn.
- Hình ảnh trích từ file trực quan hóa đồ thị (toàn cảnh và một cụm con tiêu
  biểu liên quan đến chuyển đổi số).

**Hình 3.1:** Toàn cảnh đồ thị thí điểm.
**Hình 3.2:** Một cụm con minh họa quan hệ nhân quả xoay quanh một concept.
**Bảng 3.8:** Thống kê node/edge/quan hệ thành phần của đồ thị thí điểm.

## 3.8. Đánh giá và thảo luận

### 3.8.1. Kiểm tra khả năng overfit của luật trích xuất và phân rã

- Vì luật trích xuất quan hệ và luật/từ điển phân rã concept/state (Mục 3.4,
  3.5) được tinh chỉnh lặp lại trên chính một số câu quan sát được, mục này
  cần tách rõ: tập câu dùng để xây dựng và chỉnh sửa luật, và tập câu độc lập
  dùng để kiểm tra.
- Báo cáo kết quả luật trên tập câu chưa từng dùng để chỉnh sửa, so sánh với
  kết quả trên tập đã dùng để chỉnh sửa, nêu chênh lệch nếu có.

### 3.8.2. Vấn đề ground truth

- Nêu rõ cách một quan hệ, một cặp concept/state hoặc một cụm được xác nhận
  là đúng ở giai đoạn hiện tại (người thực hiện rà soát thủ công), số lượng
  mẫu đã được rà soát cho từng bước.
- Nêu hạn chế khi chưa có quy trình gán nhãn độc lập nhiều người và độ đo
  đồng thuận, và kế hoạch bổ sung ở giai đoạn tiếp theo.

### 3.8.3. So sánh với baseline

- So sánh ViT5 (student) với LLM teacher cho tách câu (Mục 3.3), để đánh giá
  mức độ đánh đổi giữa chi phí suy luận và chất lượng sau chắt lọc tri thức.
- Đối chiếu kết quả luật trích xuất S–P–O với kết quả LLM prompting trên
  cùng một tập câu (Mục 3.4), để làm rõ điểm mạnh/yếu của từng cách tiếp cận.
- Nêu rõ đóng góp của pipeline hiện tại so với việc chỉ dùng VnCoreNLP để
  phân tích cú pháp rồi trích trực tiếp: cụ thể là từ điển trigger theo miền
  nghiên cứu, tập mẫu cấu trúc được thiết kế riêng cho quan hệ nhân quả, và
  cơ chế phân rã concept/state cùng gom nhóm tự động phía sau.

### 3.8.4. Phân tích lỗi theo từng bước

- Tổng hợp các loại lỗi đã ghi nhận ở Mục 3.3–3.7 theo bước, ước lượng mức độ
  lỗi lan truyền giữa các bước (ví dụ câu tách sai làm sai quan hệ, quan hệ
  sai làm sai concept candidate, concept candidate sai làm sai cụm).

### 3.8.5. Hạn chế do quy mô dữ liệu thí điểm

- Nêu rõ những kết luận nào chỉ có giá trị tham khảo ở quy mô hiện tại và cần
  kiểm chứng lại khi mở rộng corpus.

**Bảng 3.9:** So sánh định lượng ViT5/luật trích xuất với LLM baseline trên
tập mẫu chung.

## 3.9. Hạn chế và hướng thực nghiệm tiếp theo

- Fine-tune mREBEL và PhoBERT–BIO theo dữ liệu distillation đã thiết kế ở
  Chương 2, sau khi có đủ dữ liệu gán nhãn, để thay thế phần luật còn lại ở
  Mục 3.4 và 3.5.
- Mở rộng corpus từ danh sách liên kết đã thu thập được sang tải và xử lý ở
  quy mô đầy đủ.
- Xây dựng và đánh giá mô-đun phân tích yếu tố trực tiếp/gián tiếp trên đồ
  thị (nội dung đã lược bỏ khỏi chương này).
- Xây dựng bộ đánh giá định lượng độc lập (P/R/F1...) đầy đủ cho các bước còn
  lại theo giao thức đã đề xuất ở Mục 2.9.

---

# Danh sách bảng/hình dự kiến

1. **Bảng 3.1:** Thống kê corpus thực nghiệm.
2. **Bảng 3.2:** Kết quả tách câu của ViT5 so với LLM teacher.
3. **Bảng 3.3:** Thống kê quan hệ trích xuất theo từng mẫu cấu trúc.
4. **Bảng 3.4:** Ví dụ đối chiếu kết quả luật và LLM trên cùng một câu.
5. **Bảng 3.5:** Thống kê concept candidate và state tách được.
6. **Bảng 3.6:** Cấu hình clustering cuối cùng và thống kê cụm.
7. **Bảng 3.7:** Kết quả đánh giá thủ công trên mẫu cụm.
8. **Hình 3.1:** Toàn cảnh đồ thị thí điểm.
9. **Hình 3.2:** Một cụm con minh họa quan hệ nhân quả.
10. **Bảng 3.8:** Thống kê node/edge/quan hệ thành phần của đồ thị.
11. **Bảng 3.9:** So sánh định lượng với LLM baseline.

---

# Các quyết định cần chốt trước khi viết chi tiết Chương 3

1. Có mở rộng corpus lên quy mô đầy đủ (toàn bộ liên kết đã thu thập) trước
   khi viết Chương 3, hay giữ nguyên quy mô thí điểm và nêu rõ giới hạn.
2. Thuật toán clustering cụ thể và bộ siêu tham số cuối cùng cho Mục 3.6 có
   được chốt trước khi viết Chương 3 hay không.
3. Tập dev/test dùng để đánh giá ViT5 (Mục 3.3) đã được rà soát và tách độc
   lập với dữ liệu dùng để fine-tune hay chưa.
4. Có đủ thời gian tách tập câu dùng để chỉnh luật S–P–O/concept–state và tập
   câu kiểm tra độc lập cho Mục 3.8.1 hay không.
5. Có đưa phần so sánh với LLM prompting vào như một baseline chính thức
   trong luận văn, hay chỉ dùng để thảo luận nội bộ.

---

# Ranh giới với Chương 2 (Phương pháp thực hiện)

Chương 3 không mô tả lại: mục tiêu, framework, mô hình lý thuyết, giải thuật,
schema dữ liệu hay giao thức đánh giá — những nội dung này thuộc Chương 2.
Chương 3 chỉ báo cáo: cấu hình đã chạy, dữ liệu đã xử lý, số liệu quan sát
được, ví dụ minh họa và lỗi thực tế, cùng khoảng cách giữa phương án đề xuất
và những gì đã triển khai tại thời điểm viết luận văn.
