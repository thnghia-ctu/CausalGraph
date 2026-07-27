# ĐỀ XUẤT MỤC LỤC CHƯƠNG 2 – PHƯƠNG PHÁP THỰC HIỆN

## Định hướng tổ chức chương

Chương 2 được tổ chức theo các phương pháp nghiên cứu, không theo cấu trúc mã
nguồn. Toàn bộ chương cần trả lời ba câu hỏi:

1. Corpus và các tập dữ liệu chuẩn được xây dựng như thế nào?
2. Tri thức quan hệ được khai phá, khái quát hóa và tổ chức thành đồ thị như thế nào?
3. Các yếu tố liên quan đến quyết định ứng dụng công cụ số được nhận diện và phân tích như thế nào?

Mỗi phương pháp chính cần trình bày:

- mục tiêu;
- đầu vào và đầu ra;
- framework minh họa ở mức khái quát;
- mô hình hoặc quy tắc xử lý;
- giải thuật khi cần;
- cơ chế kiểm soát chất lượng;
- quan hệ với bước tiếp theo.

> **Lưu ý thuật ngữ:** Đồ thị trong luận văn tổ chức các quan hệ nhân quả được
> phát biểu trong corpus. Đồ thị không tự chứng minh quan hệ nhân quả ngoài thực tế.

---

# CHƯƠNG 2. PHƯƠNG PHÁP THỰC HIỆN

## 2.1. Tổng quan khung phương pháp đề xuất

Mục này trình bày ngắn gọn mục tiêu, đầu vào, đầu ra và toàn bộ pipeline của
luận văn. Không chia thành nhiều tiểu mục đánh số.

Framework tổng thể:

```text
Văn bản tiếng Việt
        ↓
Xây dựng corpus và tập dữ liệu chuẩn
        ↓
Phân rã câu phức bằng teacher–student knowledge distillation
        ↓
Trích xuất quan hệ S–P–O bằng mREBEL
        ↓
Nhận diện concept_candidate/state bằng PhoBERT–BIO
        ↓
Biểu diễn embedding cho concept_candidate
        ↓
Gom nhóm ngữ nghĩa và hình thành concept
        ↓
Hợp nhất các quan hệ theo cặp concept
        ↓
Xây dựng đồ thị phát biểu nhân quả có provenance
        ↓
Phân tích các yếu tố liên quan đến quyết định ứng dụng công cụ số
        ↓
Đánh giá và kiểm chứng kết quả
```

Phát biểu trung gian sau bước nhận diện concept/state:

```text
(source_concept_candidate, source_state)
        ── predicate ──>
(target_concept_candidate, target_state)
```

Sau bước gom nhóm, mỗi `concept_candidate` được gắn thêm một `concept_id`.
`Concept_candidate` không bị thay thế hoặc xóa. Nó tiếp tục được lưu cùng state,
predicate, câu nguồn và tài liệu nguồn.

**Hình 2.1:** Khung tổng thể của phương pháp đề xuất.

---

## 2.2. Phương pháp xây dựng corpus và tập dữ liệu chuẩn

### 2.2.1. Xác định phạm vi và nguồn dữ liệu

- Miền dữ liệu và phạm vi sản xuất lúa gạo.
- Chủ thể được xem xét.
- Khoảng thời gian thu thập.
- Tiêu chí lựa chọn nguồn.
- Tiêu chí loại bỏ tài liệu ngoài phạm vi.

### 2.2.2. Thu thập và quản lý dữ liệu

- Thu thập bài báo và văn bản trực tuyến.
- Lưu nội dung, URL, tiêu đề, nguồn, ngày đăng và ngày thu thập.
- Gán định danh tài liệu.
- Quản lý provenance.
- Kiểm soát lỗi tải và nội dung trống.

### 2.2.3. Làm sạch và lọc corpus

- Loại bỏ nội dung điều hướng, quảng cáo và thành phần không liên quan.
- Chuẩn hóa mã hóa, khoảng trắng và ký tự.
- Phân đoạn tài liệu thành đoạn và câu.
- Phát hiện tài liệu trùng hoặc gần trùng.
- Lọc mức độ liên quan đến miền nghiên cứu.

### 2.2.4. Xây dựng schema gán nhãn

Ba tập dữ liệu supervised chính:

1. Câu phức và danh sách câu đơn tương ứng.
2. Câu đơn và một hoặc nhiều bộ ba `subject – predicate – object`.
3. Subject/object và nhãn BIO cho `concept_candidate – state`.

Bước gom nhóm concept candidate không yêu cầu một controlled vocabulary hoặc
gold mapping bao phủ toàn bộ corpus. Dữ liệu đánh giá clustering có thể được xây
dựng trên một mẫu cluster hoặc một mẫu cặp candidate để kiểm tra lỗi gộp sai và
tách sai.

### 2.2.5. Quy trình gán nhãn và kiểm soát chất lượng

- Xây dựng hướng dẫn gán nhãn và các ví dụ minh họa.
- Gán thử trên một tập nhỏ để hiệu chỉnh hướng dẫn.
- Rà soát dữ liệu theo phạm vi nguồn lực thực tế.
- Khi có nhiều người tham gia, sử dụng một tập giao nhau để kiểm tra mức độ thống nhất.
- Đo độ đồng thuận và xử lý bất đồng khi dữ liệu và nguồn lực cho phép.
- Tạo tập tham chiếu đã được kiểm tra để huấn luyện và đánh giá mô hình.

### 2.2.6. Chia tập dữ liệu

- Chia train/dev/test theo tài liệu.
- Không để các câu từ cùng tài liệu xuất hiện ở nhiều tập.
- Các tài liệu trùng hoặc gần trùng phải nằm trong cùng một tập.
- Tách corpus khai phá khỏi các tập gold standard.
- Không sử dụng tập test để tối ưu prompt, mô hình, ngưỡng hoặc cấu hình.

**Hình 2.2:** Quy trình xây dựng corpus và tập dữ liệu chuẩn.

**Algorithm 1:** Xây dựng corpus và gold standard có kiểm soát chất lượng.

**Đầu vào:** Danh sách nguồn, truy vấn thu thập và schema gán nhãn.  
**Đầu ra:** Corpus đã làm sạch, metadata và các tập train/dev/test đã duyệt.

---

## 2.3. Phương pháp phân rã câu phức bằng chắt lọc tri thức

### 2.3.1. Phát biểu bài toán

- Đầu vào: một câu phức tiếng Việt.
- Đầu ra: danh sách câu đơn bảo toàn nội dung.
- Không đảo chiều nguyên nhân–kết quả.
- Không làm mất định lượng, phủ định, mức độ hoặc tham chiếu.
- Không biến hệ quả gián tiếp thành tác động trực tiếp.

### 2.3.2. Mô hình teacher

- Thiết kế prompt cho LLM.
- Quy định schema đầu ra.
- Sinh các câu đơn ứng viên.
- Kiểm tra các lỗi thêm, mất hoặc thay đổi nội dung.

### 2.3.3. Xây dựng dữ liệu distillation

```text
Câu phức
   ↓
LLM teacher sinh câu đơn
   ↓
Kiểm tra định dạng và các ràng buộc cơ bản
   ↓
Rà soát mẫu hoặc các trường hợp không chắc chắn
   ↓
Hiệu chỉnh, loại bỏ kết quả không đạt yêu cầu
   ↓
Cặp huấn luyện câu phức → danh sách câu đơn
```

### 2.3.4. Mô hình student

- Lựa chọn BARTpho hoặc ViT5.
- Fine-tune trên dữ liệu distillation đã qua các bước kiểm tra phù hợp.
- Sử dụng tập phát triển để lựa chọn checkpoint.
- Giữ tập kiểm thử độc lập.

### 2.3.5. Suy luận và kiểm tra đầu ra

- Kiểm tra đầu ra rỗng hoặc lặp.
- Kiểm tra thông tin bị thêm hoặc bị mất.
- Kiểm tra phủ định, số liệu và tham chiếu.
- Kiểm tra chiều nguyên nhân–kết quả.
- Đánh dấu trường hợp cần rà soát.

**Hình 2.3:** Framework teacher–student cho phân rã câu phức.

**Algorithm 2:** Phân rã câu phức bằng knowledge distillation.

**Đầu vào:** Câu phức tiếng Việt.  
**Đầu ra:** Danh sách câu đơn.

---

## 2.4. Phương pháp trích xuất quan hệ nhân quả bằng mREBEL

### 2.4.1. Phát biểu bài toán và schema quan hệ

Mô hình nhận câu đơn và sinh:

```text
subject – predicate – object
```

Subject và object là vai trò ngữ nghĩa được định hướng theo chiều nguyên nhân →
kết quả, không chỉ là chủ ngữ và tân ngữ cú pháp.

### 2.4.2. Xây dựng dữ liệu huấn luyện S–P–O

- Xác định đơn vị gán nhãn.
- Quy định ranh giới subject, predicate và object.
- Xử lý câu có nhiều quan hệ.
- Bổ sung câu không có quan hệ làm mẫu âm.
- Không bổ sung thành phần bằng suy diễn ngoài câu.
- Chuyển dữ liệu sang định dạng huấn luyện mREBEL.

### 2.4.3. Tuyến tính hóa đầu ra

- Quy định thứ tự subject, predicate và object.
- Quy định dấu hoặc token phân cách.
- Biểu diễn nhiều bộ ba.
- Biểu diễn trường hợp không có quan hệ.

### 2.4.4. Fine-tune mREBEL

- Khởi tạo từ mô hình pretrained.
- Fine-tune theo schema của luận văn.
- Lựa chọn checkpoint trên tập phát triển.
- Giữ tập kiểm thử độc lập.

### 2.4.5. Giải mã và kiểm tra quan hệ

- Phục hồi các bộ ba từ chuỗi sinh.
- Kiểm tra các trường bắt buộc.
- Loại bỏ kết quả lỗi định dạng hoặc rỗng.
- Xử lý bộ ba trùng lặp.
- Liên kết với câu đơn, câu gốc và tài liệu nguồn.

### 2.4.6. Baseline trích xuất quan hệ

Dependency parsing và trigger chỉ được giữ nếu dùng làm baseline hoặc phương pháp
đối chứng trong thực nghiệm.

**Hình 2.4:** Quy trình fine-tune và suy luận mREBEL theo schema nhân quả.

**Algorithm 3:** Trích xuất quan hệ nhân quả bằng mREBEL.

**Đầu vào:** Câu đơn.  
**Đầu ra:** Một hoặc nhiều bộ ba `subject – predicate – object`.

---

## 2.5. Phương pháp nhận diện concept candidate và state

### 2.5.1. Phát biểu bài toán gán nhãn chuỗi

Mô hình được áp dụng riêng cho subject và object với schema:

```text
B-CONCEPT, I-CONCEPT
B-STATE,   I-STATE
O
```

Span `CONCEPT` tạo ra `concept_candidate`; span `STATE` tạo ra trạng thái của
factor trong phát biểu cụ thể.

### 2.5.2. Thiết kế schema state

Cần quy định rõ:

- trạng thái động;
- trạng thái tĩnh;
- xu hướng;
- mức độ;
- điều kiện;
- phủ định;
- trường hợp không có state.

Phủ định phải được bảo toàn; `không tăng` không được tự động đổi thành `giảm`.

### 2.5.3. Xây dựng dữ liệu BIO

- Lấy subject và object từ dữ liệu quan hệ đã được rà soát.
- Token hóa factor.
- Gán nhãn span concept candidate và state.
- Kiểm tra ranh giới span.
- Căn chỉnh nhãn với token hoặc subword.
- Liên kết factor với relation và tài liệu nguồn.

### 2.5.4. Fine-tune PhoBERT

- PhoBERT làm encoder.
- Lớp token classification dự đoán nhãn BIO.
- Fine-tune trên tập dữ liệu đã gán nhãn.
- Lựa chọn mô hình dựa trên tập phát triển.

### 2.5.5. Hậu xử lý

- Ghép token BIO thành span.
- Xử lý chuỗi BIO không hợp lệ ở mức cú pháp.
- Khôi phục văn bản concept candidate và state.
- Không sinh state khi văn bản không biểu đạt state.
- Gắn kết quả trở lại factor ban đầu.

**Hình 2.5:** Framework nhận diện concept candidate/state bằng PhoBERT–BIO.

**Algorithm 4:** Phân rã factor thành concept candidate và state.

**Đầu vào:** Văn bản của subject hoặc object.  
**Đầu ra:** `Concept_candidate` và state tương ứng.

---

## 2.6. Phương pháp hình thành concept từ dữ liệu bằng gom nhóm ngữ nghĩa

### 2.6.1. Phát biểu bài toán

Đầu vào là tập các `concept_candidate` được tạo ở Mục 2.5. Đầu ra là các concept
cluster dùng để hình thành node của đồ thị.

Mỗi concept cluster gồm tối thiểu:

```text
concept_id
representative_label
member_concept_candidates
```

`Concept_candidate` không bị thay thế hoặc xóa sau khi được gắn với một cluster.

Cần phân biệt biểu thức candidate duy nhất với các lần xuất hiện của candidate
trong relation. Quá trình embedding và clustering có thể được thực hiện trên tập
các biểu thức candidate duy nhất sau chuẩn hóa hình thức, trong khi liên kết đến
mọi lần xuất hiện ban đầu vẫn được duy trì để gắn kết quả trở lại factor và
relation.

### 2.6.2. Chuẩn hóa hình thức concept candidate

- Chuẩn hóa chữ hoa/chữ thường khi cần.
- Chuẩn hóa khoảng trắng và ký tự.
- Loại bỏ khác biệt trình bày không làm thay đổi nghĩa.
- Không loại bỏ các thành phần làm thay đổi nội dung concept.
- Có thể hợp nhất các biểu thức candidate trùng lặp hoàn toàn trước khi clustering,
  nhưng vẫn giữ liên kết đến toàn bộ các lần xuất hiện ban đầu.

### 2.6.3. Biểu diễn ngữ nghĩa

- Sinh embedding từ chính chuỗi `concept_candidate`.
- Không đưa state, predicate, concept ở đầu còn lại hoặc câu nguồn vào embedding
  dùng để hình thành node.
- State và ngữ cảnh được bảo toàn trong relation thành phần, nhưng không quyết
  định danh tính node.

### 2.6.4. Gom nhóm concept candidate

- Lựa chọn thuật toán clustering phù hợp.
- Không bắt buộc biết trước số nhóm nếu phương pháp được chọn không yêu cầu.
- Cho phép candidate không đủ tương đồng tạo thành singleton cluster.
- Không ép mọi candidate vào một nhóm lớn.
- Phân tích ảnh hưởng của ngưỡng, số nhóm, seed hoặc cấu hình khi phù hợp.

### 2.6.5. Lựa chọn nhãn đại diện

Nhãn đại diện được chọn từ dữ liệu thành viên, chẳng hạn:

- candidate có tần suất cao;
- candidate gần tâm nhóm;
- medoid của nhóm.

Quy tắc cuối cùng được chốt trong thực nghiệm. Nhãn đại diện chỉ dùng để hiển
thị, không thay thế các candidate thành phần.

### 2.6.6. Gắn concept ID trở lại dữ liệu quan hệ

- Gán `concept_id` cho từng factor.
- Giữ nguyên `concept_candidate`.
- Giữ nguyên state, predicate, câu và tài liệu nguồn.
- Cho phép truy ngược từ concept cluster đến mọi lần xuất hiện thành phần.

### 2.6.7. Nguyên tắc diễn giải cluster

- Không mặc định các candidate trong cùng cluster hoàn toàn đồng nghĩa.
- Cluster là lớp khái quát phục vụ tổ chức và trực quan hóa dữ liệu.
- Khi người dùng chọn node, hệ thống hiển thị các candidate thành phần.
- Những cluster quá rộng hoặc thiếu nhất quán phải được phân tích trong phần lỗi.

**Hình 2.6:** Quy trình hình thành concept từ dữ liệu bằng gom nhóm ngữ nghĩa.

**Algorithm 5:** Gom nhóm ngữ nghĩa các concept candidate và hình thành concept.

**Đầu vào:** Tập `concept_candidate`.  
**Đầu ra:** Các concept cluster và phép gắn `concept_candidate → concept_id`.

---

## 2.7. Phương pháp xây dựng đồ thị phát biểu nhân quả

### 2.7.1. Mô hình đồ thị

Sử dụng đồ thị có hướng:

```text
G = (V, E)
```

Trong đó:

- mỗi node là một concept cluster;
- mỗi edge là liên kết tổng hợp giữa một cặp concept;
- mỗi edge giữ tập các relation hoặc evidence thành phần.

### 2.7.2. Thiết kế node

Node chứa tối thiểu:

```text
concept_id
representative_label
member_concept_candidates
```

Không tạo node riêng cho từng tổ hợp `concept + state`.

Khi người dùng chọn node, hệ thống có thể hiển thị các concept candidate thành
phần và các lần xuất hiện tương ứng.

### 2.7.3. Gắn relation vào các concept cluster

Mỗi relation sau bước 2.6 giữ:

```text
source_concept_id
source_concept_candidate
source_state
predicate
target_concept_id
target_concept_candidate
target_state
simple_sentence
original_sentence
document_id/source
```

### 2.7.4. Hợp nhất quan hệ và thiết kế edge

Các relation có cùng cặp:

```text
(source_concept_id, target_concept_id)
```

được tập hợp vào một cạnh ở tầng khái quát. Đây là phương án biểu diễn chính để
giữ đồ thị gọn và hỗ trợ quan sát tổng quan. Những relation khác nhau về state
hoặc predicate vẫn được lưu riêng trong danh sách evidence của cạnh và có thể
được phân nhóm khi hiển thị. Phương án multigraph chỉ được xem xét trong thực
nghiệm nếu việc gộp vào một cạnh làm mất khả năng diễn giải.

Mỗi cạnh phải giữ riêng các relation thành phần; không được ghi đè:

- predicate;
- source state;
- target state;
- concept candidate;
- câu đơn;
- câu gốc;
- tài liệu nguồn.

Khi người dùng chọn cạnh, hệ thống hiển thị các relation và câu nguồn thuộc cạnh.

### 2.7.5. Tổ chức bằng chứng và provenance

- Giữ định danh relation thành phần.
- Giữ liên kết với câu đơn, câu gốc và tài liệu.
- Ghi nhận phiên bản pipeline khi phù hợp.
- Tổng hợp số relation và số nguồn như thống kê corpus.
- Không đồng nhất tần suất với cường độ tác động nhân quả.

### 2.7.6. Kiểm tra tính hợp lệ của đồ thị

- Node phải có `concept_id`, nhãn đại diện và ít nhất một candidate.
- Edge phải có ít nhất một relation thành phần.
- Không tạo cạnh từ relation thiếu source hoặc target.
- Không làm mất state, predicate hoặc provenance.
- Phát hiện relation trùng lặp và xung đột.
- Self-loop và chu trình được đánh dấu để rà soát, không tự động xem là sai.
- Singleton cluster được xem là node hợp lệ.

**Hình 2.7:** Framework xây dựng đồ thị có provenance và evidence drill-down.

**Algorithm 6:** Xây dựng đồ thị từ các concept cluster và relation thành phần.

**Đầu vào:** Các relation đã được gắn `concept_id` và metadata nguồn.  
**Đầu ra:** Đồ thị có hướng cùng tập evidence truy vết.

---

## 2.8. Phương pháp phân tích các yếu tố chi phối

### 2.8.1. Xác định node quyết định và phạm vi chủ thể

- Xác định concept cluster biểu diễn quyết định ứng dụng công cụ số.
- Phân biệt nông dân, nông hộ, hợp tác xã và doanh nghiệp khi cần.
- Xác định một node đích chung hoặc nhiều node đích theo chủ thể.
- Kiểm tra các candidate thành phần của node quyết định.

### 2.8.2. Nhận diện yếu tố trực tiếp

Yếu tố trực tiếp là node có cạnh hướng đến node quyết định trong phạm vi phân tích.

Kết quả phải kèm:

- các relation thành phần;
- số bằng chứng;
- số nguồn độc lập;
- state và predicate;
- câu và tài liệu đại diện.

### 2.8.3. Nhận diện yếu tố gián tiếp

Yếu tố gián tiếp là node có đường đi hướng đến node quyết định qua một hoặc
nhiều node trung gian.

Cần quy định:

- độ dài đường đi được xem xét;
- điều kiện tương thích về chủ thể và bằng chứng;
- xử lý nhiều đường đi;
- cách trình bày các relation thành phần trên từng cạnh.

Đường đi chỉ tạo ra ứng viên tác động gián tiếp trong corpus, không tự chứng minh
quan hệ trung gian ngoài thực tế.

### 2.8.4. Thống kê và ưu tiên các yếu tố

Ở mức tối thiểu, các yếu tố được mô tả bằng số relation thành phần, số nguồn và
mức độ trực tiếp hoặc gián tiếp đối với node quyết định. Khi cần xây dựng một
điểm ưu tiên, các thành phần có thể được lựa chọn từ:

- số lượng relation thành phần;
- số nguồn độc lập;
- độ tin cậy của mô hình nếu có;
- mức độ trực tiếp hoặc gián tiếp;
- sự nhất quán của state và predicate.

Công thức tổng hợp chỉ được sử dụng khi có cơ sở và được kiểm chứng trong thực
nghiệm. Điểm ưu tiên, nếu có, không được diễn giải như cường độ tác động nhân
quả thực tế.

### 2.8.5. Phân tích nhóm yếu tố

Các concept cluster được khai phá từ corpus có thể được tổ chức hoặc diễn giải
ở cấp cao hơn sau khi đồ thị đã được xây dựng.

Việc đối chiếu với TAM, UTAUT, TOE, DOI hoặc một khung lý thuyết khác chỉ được
thực hiện khi luận văn lựa chọn rõ một khung phù hợp và có đủ cơ sở diễn giải.
Đây là bước hậu nghiệm ở tầng phân tích, không phải vocabulary dùng để hình
thành node và cũng không bắt buộc đối với toàn bộ pipeline.

### 2.8.6. Phân tích độ nhạy và tính ổn định

Phân tích tối thiểu tập trung vào ảnh hưởng của cấu hình clustering đến node,
edge và các yếu tố được nhận diện. Tùy nguồn lực thực nghiệm, có thể xem xét thêm:

- thay đổi mô hình embedding;
- thay đổi thuật toán, ngưỡng, số nhóm hoặc seed;
- thay đổi độ dài đường đi;
- thay đổi cách tổng hợp bằng chứng;
- loại từng nguồn dữ liệu.

Không bắt buộc thực hiện đồng thời mọi biến thể. Các cấu hình được lựa chọn cần
phù hợp với mục tiêu và nguồn lực thực tế của luận văn.

### 2.8.7. Trình bày kết quả có truy vết

Mỗi kết luận cần đi kèm:

- concept cluster và các candidate thành phần;
- vị trí trên đồ thị;
- cạnh hoặc đường tác động;
- relation thành phần;
- state và predicate;
- câu và tài liệu nguồn.

**Hình 2.8:** Framework phân tích yếu tố trực tiếp, gián tiếp và bằng chứng.

**Algorithm 7:** Nhận diện, tổng hợp và ưu tiên các yếu tố liên quan đến quyết định ứng dụng công cụ số.

**Đầu vào:** Đồ thị có hướng, node quyết định và tập evidence.  
**Đầu ra:** Danh sách yếu tố trực tiếp/gián tiếp, thông tin ưu tiên nếu có và bằng chứng hỗ trợ.

---

## 2.9. Phương pháp đánh giá và kiểm chứng

Phần đánh giá được tổ chức theo mức ưu tiên để bảo đảm phù hợp với phạm vi và
nguồn lực của luận văn. Tập kiểm thử phải độc lập với dữ liệu dùng để điều chỉnh
prompt, mô hình, ngưỡng hoặc cấu hình thuật toán.

### 2.9.1. Nhóm đánh giá bắt buộc

#### a. Đánh giá phân rã câu

- Độ trung thành ngữ nghĩa.
- Độ đầy đủ thông tin.
- Độ chính xác về phủ định, định lượng và tham chiếu.
- Độ chính xác về chiều nguyên nhân--kết quả.
- Phân tích các trường hợp thêm, mất hoặc thay đổi nội dung.

#### b. Đánh giá trích xuất S--P--O

- Precision, Recall và F1 theo span.
- Exact match của bộ ba.
- Đánh giá câu có nhiều quan hệ và câu không có quan hệ.
- Phân tích lỗi định hướng và lỗi giải mã.

#### c. Đánh giá concept candidate/state

- Precision, Recall và F1 theo token hoặc span.
- Kết quả riêng cho concept candidate và state.
- Độ chính xác của phủ định, mức độ và ranh giới span.

#### d. Đánh giá gom nhóm concept candidate trên mẫu

- Mức nhất quán ngữ nghĩa trong một mẫu cluster.
- Lỗi gộp sai và lỗi tách sai.
- Tỷ lệ singleton cluster và phân bố kích thước cluster.
- Đánh giá thủ công trên một tập cluster đại diện.
- Chỉ số clustering nội tại chỉ được dùng như thông tin hỗ trợ.

#### e. Đánh giá bảo toàn relation và provenance

- Tỷ lệ relation thành phần được giữ sau khi hợp nhất.
- Khả năng truy xuất concept candidate từ node.
- Khả năng truy xuất relation, câu và tài liệu nguồn từ edge.
- Kiểm tra node, edge, relation trùng lặp và bằng chứng xung đột.
- Phân tích lỗi phát sinh và lỗi lan truyền giữa các bước.

### 2.9.2. Nhóm đánh giá nên thực hiện

- So sánh một số cấu hình embedding hoặc clustering phù hợp.
- Kiểm tra độ ổn định của cluster khi thay đổi ngưỡng, số nhóm hoặc seed.
- So sánh số node và mức phân mảnh trước và sau clustering.
- Đánh giá end-to-end trên một mẫu từ câu gốc đến relation, concept cluster và
  edge tổng hợp.
- Kiểm tra thủ công một mẫu yếu tố trực tiếp, yếu tố gián tiếp và đường đi có
  truy vết đầy đủ.

### 2.9.3. Nhóm đánh giá mở rộng khi đủ nguồn lực

- So sánh student với LLM teacher hoặc baseline.
- So sánh mREBEL với dependency/trigger baseline.
- Thực hiện ablation trên một số thành phần chính của pipeline.
- Đánh giá bởi chuyên gia đối với cluster, node, edge và kết quả phân tích.
- Phân tích độ nhạy theo nhiều nguồn dữ liệu hoặc nhiều cách tổng hợp bằng chứng.

Các đánh giá mở rộng chỉ được triển khai khi có đủ dữ liệu, thời gian và nguồn
lực. Việc không thực hiện toàn bộ các nội dung này không làm thay đổi kiến trúc
cốt lõi của phương pháp.

### 2.9.4. Nguyên tắc báo cáo kết quả

- Chỉ so sánh các phương pháp trên cùng dữ liệu và tiêu chí.
- Không sử dụng tập test để lựa chọn cấu hình.
- Phân biệt kết quả của từng mô-đun với kết quả end-to-end.
- Báo cáo cả chỉ số định lượng và các trường hợp lỗi điển hình.
- Không diễn giải tần suất, centrality hoặc điểm mô hình như cường độ tác động
  nhân quả ngoài thực tế.
- Mọi kết luận về node, edge hoặc yếu tố phải có khả năng truy vết về dữ liệu nguồn.

**Hình 2.9:** Framework đánh giá đa tầng theo mức ưu tiên.

Thay vì xây dựng một giải thuật riêng cho phần đánh giá, giao thức đánh giá nên
được trình bày bằng bảng liên kết giữa tác vụ, dữ liệu kiểm thử, tiêu chí và mục
tiêu đánh giá trong chương Thực nghiệm.

---

# Danh sách framework dự kiến

1. **Hình 2.1:** Khung tổng thể của phương pháp đề xuất.
2. **Hình 2.2:** Quy trình xây dựng corpus và gold standard.
3. **Hình 2.3:** Framework teacher–student cho phân rã câu.
4. **Hình 2.4:** Framework trích xuất quan hệ bằng mREBEL.
5. **Hình 2.5:** Framework nhận diện concept candidate/state bằng PhoBERT–BIO.
6. **Hình 2.6:** Framework hình thành concept bằng gom nhóm ngữ nghĩa.
7. **Hình 2.7:** Framework xây dựng đồ thị có provenance và evidence drill-down.
8. **Hình 2.8:** Framework phân tích các yếu tố và bằng chứng.
9. **Hình 2.9:** Framework đánh giá đa tầng theo mức ưu tiên.

# Danh sách giải thuật dự kiến

1. **Algorithm 1:** Xây dựng corpus và gold standard.
2. **Algorithm 2:** Phân rã câu phức bằng knowledge distillation.
3. **Algorithm 3:** Trích xuất quan hệ nhân quả bằng mREBEL.
4. **Algorithm 4:** Phân rã factor thành concept candidate và state.
5. **Algorithm 5:** Gom nhóm ngữ nghĩa các concept candidate và hình thành concept.
6. **Algorithm 6:** Xây dựng đồ thị từ concept cluster và relation thành phần.
7. **Algorithm 7:** Nhận diện, tổng hợp và ưu tiên các yếu tố liên quan đến quyết định ứng dụng.

---

# Các quyết định cần chốt với giảng viên hướng dẫn

1. Chủ thể ra quyết định chính và phạm vi của từng nhóm chủ thể.
2. Một node quyết định chung hay nhiều node theo chủ thể.
3. Định nghĩa thao tác chính thức của “yếu tố chi phối”.
4. Schema state, phủ định, mức độ và predicate.
5. Mô hình embedding dùng cho concept candidate.
6. Thuật toán clustering.
7. Cách lựa chọn số nhóm hoặc ngưỡng gom nhóm.
8. Có gom chung concept candidate ở source và target hay thực hiện riêng.
9. Quy tắc chọn `representative_label`.
10. Cách xử lý singleton cluster.
11. Chính sách hợp nhất các relation có cùng cặp cluster nhưng khác state hoặc predicate.
12. Giữ một edge tổng hợp cho mỗi cặp node hay sử dụng multigraph trong các trường hợp cần tách relation theo state hoặc predicate.
13. Điều kiện hợp lệ của đường tác động gián tiếp.
14. Cách xác định nguồn độc lập, trọng số bằng chứng và điểm xếp hạng.
15. Vai trò của TAM, UTAUT, TOE hoặc DOI trong tầng diễn giải kết quả.
16. Quy mô dữ liệu, số người gán nhãn và cách xử lý bất đồng.
17. Phạm vi đánh giá bắt buộc, đánh giá nên thực hiện và đánh giá mở rộng.
18. Baseline, ablation và bộ chỉ số đánh giá chính thức.

---

# Ranh giới với chương Thực nghiệm và Kết quả

Chương 2 mô tả:

- phương pháp;
- mô hình;
- framework;
- giải thuật;
- giao thức đánh giá;
- cách xây dựng dữ liệu;
- các quyết định thiết kế cần kiểm chứng.

Các nội dung sau nên chuyển sang chương Thực nghiệm/Kết quả:

- cấu hình phần cứng và phần mềm;
- mô hình embedding và thuật toán clustering cuối cùng nếu được chọn qua thực nghiệm;
- giá trị ngưỡng, số nhóm hoặc siêu tham số cuối cùng;
- số epoch, batch size và thời gian huấn luyện;
- kết quả định lượng;
- bảng so sánh mô hình;
- số node, edge và cluster thực tế;
- đồ thị kết quả cuối;
- danh sách và thứ hạng yếu tố;
- phân tích lỗi dựa trên kết quả thực nghiệm.
