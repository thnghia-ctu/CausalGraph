# Kế hoạch chuẩn hóa và cải thiện Pattern A (`direct_svo`)

## Mục đích tài liệu

Tài liệu này lưu lại kết quả đánh giá Pattern A trên `output/relations.csv`, nguyên nhân gốc trong matcher/handler và kế hoạch cải thiện để làm cơ sở cho các lần trao đổi và triển khai tiếp theo.

Phạm vi mã nguồn đã xem xét:

- `src/extraction/causal_patterns.py`
- `src/extraction/dependency_tree.py`
- `src/extraction/relation_extractor.py`
- `output/relations.csv`

Đơn vị đánh giá chính là **cặp câu–trigger duy nhất**, vì một câu có thể chứa nhiều trigger và dữ liệu có một số câu trùng giữa các tài liệu.

## Tổng quan kết quả

| Chỉ số | Không tính bản lặp | Tính toàn bộ dòng CSV |
|---|---:|---:|
| Tổng trường hợp thuộc Pattern A | 78 | 88 |
| Nhận diện và trích xuất tốt | 9 | 11 |
| Nhận diện đúng nhưng trích xuất chưa tốt | 44 | 45 |
| Bị Pattern A bỏ sót | 25 | 32 |

Thông tin bổ sung:

- `relations.csv` có 330 dòng.
- 56 dòng được gán `direct_svo`, tương ứng 53 cặp câu–trigger duy nhất.
- Ba bản lặp là dòng 60/78, 67/85 và 75/93.
- Tỷ lệ trích xuất đúng hoàn toàn trong các trường hợp đã nhận diện: **9/53 = 17,0%**.
- Recall matcher Pattern A trên tập được xác định thủ công: **53/78 = 67,9%**.
- Exact-match toàn Pattern A: **9/78 = 11,5%**.

Các số liệu trên chỉ áp dụng cho các trigger xuất hiện trong `relations.csv`. Pipeline hiện loại im lặng trigger có anchor POS không thuộc `{V, A}` trước bước classify; muốn đo recall toàn corpus cần audit thêm các trigger bị loại ở bước này.

## Logic Pattern A hiện tại

Matcher yêu cầu anchor của trigger có đồng thời:

- Ít nhất một child mang dependency `sub` hoặc `nsubj`.
- Ít nhất một child thuộc `dob`, `obj`, `ccomp`, `xcomp`, `pob`; nếu không có thì tìm `vmod` với POS `V` hoặc `A`.

Handler sau đó luôn lấy dependent đầu tiên:

```python
source_tok = tree.find_dependents(
    anchor, roles={"sub", "nsubj"}
)[0]

target_tok = tree.find_dependents(
    anchor,
    roles={"dob", "obj", "ccomp", "xcomp", "pob", "vmod"},
)[0]
```

Source và target được mở rộng bằng toàn bộ dependency subtree của token được chọn.

## Các nguyên nhân gốc

### E1 — Handler chọn target đầu tiên thay vì event target

Với cấu trúc thường gặp:

```text
giúp/khiến/cho_phép + người/đơn vị + động từ kết quả
```

VnCoreNLP thường gắn danh từ chỉ người bằng `dob` và gắn động từ kết quả bằng `vmod`. Handler chọn `dob` vì nó đứng trước, dẫn tới target chỉ còn `nông_dân`, `họ`, `người tiêu_dùng` hoặc một cụm danh từ ngắn.

### E2 — Mất các source/target đồng cấp

`collect_subtree_ids()` chỉ lấy hậu duệ của một node. Các kết quả như `giảm`, `tăng`, `cải_thiện`, `tiết_kiệm` thường là các `vmod`, `coord` hoặc `conj` sibling của nhau, nên chỉ kết quả đầu tiên được giữ.

### E3 — Handler chọn source đầu tiên

Khi parser tạo nhiều child `sub`, handler luôn lấy phần tử đầu tiên theo thứ tự token. Điều này gây ra:

- Chọn subject của mệnh đề trước thay vì subject gần trigger.
- Chọn một thành phần cuối danh sách thay vì toàn cụm source.
- Chọn một token thuộc target làm source trong câu mệnh lệnh hoặc câu parse lỗi.

### E4 — Nhầm kiểu quan hệ

Một số trạng thái, câu mục đích, tiêu đề hoặc câu mệnh lệnh bị ép thành quan hệ nhân quả trực tiếp. Ví dụ:

- `Nhằm thúc_đẩy...` phải ưu tiên Pattern C.
- `Nhân_lực số còn hạn_chế khi...` là trạng thái kèm minh chứng, không phải `hạn_chế` gây ra mệnh đề sau.
- Câu mệnh lệnh không có source hiển ngôn không nên tạo source giả từ một `sub` do parser gán nhầm.

### E5 — Subtree quá rộng hoặc sai biên mệnh đề

Subtree thuần túy có hai vấn đề đối nghịch:

- Không lấy được sibling cần thiết.
- Có thể nuốt mệnh đề phụ chú, mệnh đề so sánh hoặc mệnh đề độc lập không thuộc source/target.

### E6 — Phân đoạn câu và tài liệu chưa tốt

URL, tiêu đề, bullet list và nhiều câu bị nối liền làm VnCoreNLP chọn sai root/head. Đây là nguyên nhân đáng kể ở các dòng 119, 129, 187, 212, 227 và 236.

## Các trường hợp trích xuất tốt

### Dòng 11

- **Câu:** `... điều này giúp tiết_kiệm tối_đa nguồn_lực.`
- **Kết quả:** `điều này — giúp — tiết_kiệm tối_đa nguồn_lực`
- **Đánh giá:** Đúng và đủ.
- **Lý do:** `điều` là `sub`; `tiết_kiệm/V` là `vmod` trực tiếp của `giúp`.

### Dòng 23

- **Câu:** `... điều này giúp tăng năng_suất lao_động đáng_kể.`
- **Kết quả:** `điều này — giúp — tăng năng_suất lao_động đáng_kể`
- **Đánh giá:** Đúng và đủ.

### Dòng 60/78

- **Câu:** `Nền_tảng này giúp nông_dân và người mua gặp_gỡ, thương_lượng, giao_dịch trực_tuyến.`
- **Kết quả:** Giữ được cả chủ thể nhúng và chuỗi hành động target.
- **Đánh giá:** Đúng. Đây là regression test quan trọng cho target phối hợp.

### Dòng 75/93

- **Câu:** `Điều này sẽ giúp tăng khả_năng hiển_thị dọc theo chuỗi cung_ứng.`
- **Đánh giá:** Source, trigger và target đều đúng.

### Dòng 77

- **Câu:** `Giải_pháp nào giúp đẩy mạnh chuyển_đổi số trong giai_đoạn tới?`
- **Đánh giá:** Trích xuất cấu trúc đúng, nhưng đây là quan hệ nghi vấn. Nên bổ sung metadata `modality=question`.

### Dòng 156

- **Câu:** `Sự chậm_trễ này đang khiến doanh_nghiệp đối_mặt với rủi_ro ngày_càng lớn.`
- **Đánh giá:** Đúng và đủ.

### Dòng 164

- **Câu:** `Việc thiếu chuẩn dữ_liệu và nền_tảng dùng chung khiến các giải_pháp khó liên_thông..., hiệu_quả kinh_tế chưa đủ rõ...`
- **Đánh giá:** Source và hai kết quả đều được giữ đúng.

### Dòng 210

- **Câu:** `Điều này đôi_khi gây ra xung_đột giá_trị giữa các thế_hệ...`
- **Đánh giá:** Đúng về nội dung. Có thể chuẩn hóa trigger thành `gây_ra`.

### Dòng 330

- **Câu:** `Việc lập bản_đồ số_hoá từng vùng giúp xác_định lộ_trình, ưu_tiên đầu_tư và lựa_chọn công_nghệ phù_hợp.`
- **Đánh giá:** Đúng và giữ được đầy đủ các hành động target.

## Các trường hợp nhận diện đúng nhưng trích xuất chưa tốt

| Dòng | Câu rút gọn | Lỗi hiện tại | Nguyên nhân/cải thiện |
|---:|---|---|---|
| 3 | `Khoảng trống này khiến người sản_xuất... rơi vào thế bị_động` | Target chỉ là `người sản_xuất` | E1; ghép `dob` với event `vmod rơi`. |
| 12 | `Điều này giúp người tiêu_dùng truy_xuất...` | Target chỉ `người tiêu_dùng` | E1; chọn `truy_xuất` làm event head. |
| 15 | `công_nghệ giúp nông_dân cài_đặt... và cảnh_báo...` | Target bị cắt | E1+E2; thu các predicate phối hợp. |
| 16 | `nền_tảng cho_phép người tiêu_dùng gửi, đặt và nhận...` | Target chỉ `người tiêu_dùng` | Frame riêng `cho_phép + beneficiary + VP`. |
| 18 | `máy thu_hoạch giúp thu_hoạch...` | Source bị lấy thành mệnh đề về `máy_cày` | E3; chọn subject gần trigger nhất. |
| 20 | `Điều này giúp họ tiết_kiệm...` | Target chỉ `họ` | E1; lấy `họ tiết_kiệm... và phản_ứng...`. |
| 25 | `giúp nông_dân kiểm_soát và cải_thiện...` | Thiếu `cải_thiện` | E1+E2. |
| 27 | `giúp độ tin_cậy..., đáp_ứng yêu_cầu...` | Target bị chia cắt | E2+E6; kiểm tra chất lượng câu trước parse. |
| 28 | `giúp họ có khả_năng theo_dõi, giám_sát...` | Target chỉ `họ` | E1; lấy VP bắt đầu từ `có`. |
| 30 | `cho_phép nông_dân khai_thác... để dự_báo...` | Thiếu mệnh đề mục đích trong target | Hợp nhất `prp` liên quan vào event target. |
| 36 | `giúp tăng_cường hiệu_quả và giảm công_sức` | Thiếu kết quả thứ hai | E2. |
| 42 | `tiếp_cận... hạn_chế, làm cho triển_khai... khó_khăn` | Trigger chính bị chọn sai thành `hạn_chế` | Quan hệ đúng dùng trigger `làm_cho`; E4. |
| 67/85 | `giúp giảm..., giảm..., tăng..., từ đó giúp tăng...` | Chỉ giữ kết quả đầu | E2; tách nhiều relation hoặc target-event list. |
| 119 | `nhà_máy thông_minh... giúp tối_ưu, ra quyết_định, giảm_thiểu...` | Chỉ giữ kết quả đầu | E2+E6. |
| 121 | `giúp kiểm_soát..., truy_xuất...` | Thiếu `truy_xuất` | E2. |
| 126 | `giúp nâng cao nhận_diện thương_hiệu` | Target chỉ `nâng cao` | Tái dựng phrase theo khoảng token liên tục. |
| 128 | `việc tối_ưu trải_nghiệm khách_hàng giúp doanh_nghiệp...` | Source sai `khách_hàng` | E3; nâng source tới ancestor danh hóa `việc`. |
| 129 | `Thông_tin trên giúp nhà_quản_lý hiểu và nắm rõ...` | Source thừa `Hy_vọng`, target thiếu danh sách | E2+E6. |
| 136 | `Nhân_lực số còn hạn_chế khi...` | Mệnh đề minh chứng bị coi là target | E4; không phải quan hệ nhân quả trực tiếp. |
| 137 | `Thiếu dữ_liệu và tiêu_chuẩn... khiến...` | Source thiếu `Thiếu dữ_liệu và` | E3; phục hồi phối hợp source. |
| 140 | `Nhằm thúc_đẩy quá_trình này...` | Source=`Nhằm` | E4; lexical guard để ưu tiên Pattern C. |
| 145 | `anh Duẩn đẩy_mạnh ứng_dụng, chuyển_đổi số, tiêu_thụ...` | Chỉ giữ hành động đầu | E2. |
| 149 | `mô_hình... giúp giám_sát đất, thuỷ_lợi, canh_tác...` | Thiếu phần lớn danh sách | E2; mở rộng enumeration cùng clause. |
| 181 | `công_nghệ giúp nông_dân tiếp_cận, thay_đổi, tìm_kiếm...` | Chỉ giữ kết quả đầu | E1+E2. |
| 187 | `ứng_dụng IoT, AI, Big Data và blockchain giúp...` | Source chỉ `Big Data`, target bị cắt | E3+E2; nâng source tới `việc ứng_dụng`. |
| 188 | `giúp giảm chi_phí, đồng_thời tăng năng_suất` | Thiếu tăng năng suất | E2. |
| 191 | `giúp hộ nông_dân bán..., giảm trung_gian và nâng cao...` | Thiếu hai kết quả cuối | E2. |
| 192 | `không_chỉ cải_thiện thu_nhập mà_còn tăng...` | Target sai thành `không_chỉ` | E1; loại liên từ khỏi ứng viên target. |
| 209 | `mất dữ_liệu hoặc bị tấn_công... gây hậu_quả..., làm mất_lòng tin...` | Source và target đều thiếu nhánh phối hợp | E2 hai phía. |
| 212 | Tiêu đề `Chính_sách đẩy_mạnh tác_động...` | Tạo relation từ heading | E6; tách heading trước parse. |
| 214 | `đồng_bộ hạ_tầng giúp nông_dân tiếp_cận...` | Target chỉ `nông_dân dễ_dàng` | E1; cho phép VP `prp` sau beneficiary. |
| 221 | `giúp sản_phẩm chè tiếp_cận dễ_dàng và nhanh_chóng` | Thiếu `nhanh_chóng` | E2. |
| 227 | Câu tập huấn rất dài | Source/target lẫn nhiều thành phần | E3+E5+E6; cần tách clause trước extraction. |
| 229 | Mệnh lệnh `Đẩy_mạnh chuyển_giao...` | Source sai `chất_lượng cao` | E3+E4; source nên là implicit hoặc loại. |
| 233 | `IoT, Big Data được ứng_dụng giúp phân_tích...` | Source chỉ `Big_Data` | E3; nâng tới cụm công nghệ/việc ứng dụng. |
| 235 | `AI giúp phân_tích..., quản_lý...` | Thiếu `quản_lý thức_ăn` | E2. |
| 236 | `Công_nghệ tự_động_hoá... giúp giảm, tiết_kiệm, bảo_đảm...` | Source sai và target chỉ kết quả đầu | E3+E2+E6. |
| 240 | `Điều này gây khó_khăn cho việc tiếp_cận...` | Target chỉ `khó_khăn` | Ghép adjective với complement `cho + NP`. |
| 242 | `chính_sách tín_dụng hỗ_trợ nông_nghiệp công_nghệ_cao...` | Target thừa/thiếu biên | Dùng frame `hỗ_trợ + beneficiary/domain`. |
| 262 | `khiến người nông_dân chịu nhiều thiệt_thòi` | Target chỉ cụm người | E1; ghép với `vmod chịu`. |
| 275 | `Một trung_tâm hỗ_trợ nhiều đơn_vị sẽ giúp giảm chi_phí` | Source thiếu `nhiều đơn_vị` | E3; tái dựng NP liên tục bên trái trigger. |
| 279 | `chúng_ta có_thể hạn_chế tối_đa việc mù_mờ...` | Target chỉ `tối_đa` | E1; ưu tiên `dob việc`, coi `tối_đa` là mức độ. |
| 288 | Mệnh lệnh `Tăng_cường sự quan_tâm, hỗ_trợ...` | Source sai `các chuyên_gia` | E3+E4; source implicit hoặc loại. |
| 302 | `Sở... đẩy_mạnh phối_hợp, đẩy nhanh, chia_sẻ, đầu_tư...` | Chỉ giữ predicate đầu | E2; thu predicate cùng subject đến biên clause. |

## Các trường hợp Pattern A bị bỏ sót

### Trigger bị gắn `nmod` vào danh từ cuối source

Các dòng: **22, 24, 40, 61/79, 63/81, 64/82, 132, 173, 174**.

Ví dụ:

- `Các công_nghệ... cho_phép nông_dân thu_thập...`: `cho_phép/V-nmod → số/N`.
- `Chuyển_đổi số giúp giảm_thiểu rủi_ro`: `giúp/V-nmod → số/N`.
- `rào_cản lớn khiến nhiều hợp_tác_xã...`: `khiến/V-nmod → rào_cản/N`.

Điều kiện làm matcher thất bại là anchor không có child `sub/nsubj`. Cách sửa an toàn là phục hồi NP bên trái khi:

- Trigger có object hoặc event target rõ.
- NP và trigger nằm trong cùng clause.
- Không có dấu chấm phẩy hay một subject/predicate độc lập chen giữa.
- Cấu trúc khớp frame đã biết như `NP + giúp/cho_phép/khiến + NP/VP`.

### Trigger bị gắn `vmod` vào predicate source

Các dòng: **9, 14, 38, 70/88, 71/89, 76/94, 98, 122, 123, 169, 197, 206, 252**.

Ví dụ:

- `Dự_báo chính_xác... có_thể giúp nông_dân...`: `giúp/V-vmod → Dự_báo/V`.
- `Chăn_nuôi chính_xác giúp thu_thập...`: `giúp/V-vmod → Chăn_nuôi/V`.
- `Thiếu hạ_tầng... đang khiến họ loay_hoay...`: `khiến/V-vmod → Thiếu/V`.

Các câu này có source hiển ngôn về mặt ngôn ngữ, nhưng dependency parser biểu diễn source như parent của trigger thay vì child `sub`. Cần hỗ trợ:

- Cụm danh hóa `Việc + VP + trigger + target`.
- NP/predicate liền trước trigger có modal `đã`, `sẽ`, `có_thể`, `đang`.
- Shared subject trong predicate phối hợp.

Không nên áp dụng phục hồi parent vô điều kiện, vì sẽ lẫn với Pattern B và Pattern C. Đặc biệt phải loại các parent/anchor nằm dưới `prp` chỉ mục đích.

### Các nhãn đặc biệt khác

#### Dòng 35

- **Câu:** `Sự kết_hợp... sẽ đem lại năng_suất tốt hơn và tăng_cường sản_lượng.`
- **Hiện tại:** `unmatched`.
- **Dependency:** `tăng_cường/V-conj`.
- **Cải thiện:** Cho predicate conjunct kế thừa subject của predicate trước.

#### Dòng 72/90

- **Câu:** `Bởi công_nghệ này giúp khai_thác các dữ_liệu...`
- **Hiện tại:** `unmatched`.
- **Dependency:** `giúp` là root nhưng source nằm dưới `Bởi/E-prp`, không phải `sub`.
- **Cải thiện:** Mẫu có guard `Bởi + NP + trigger + VP`.

#### Dòng 234

- **Câu:** `... thiết_bị GPS... đã giúp cho việc nuôi_trồng và đánh_bắt... hiệu_quả.`
- **Hiện tại:** `unmatched`.
- **Nguyên nhân:** Complement bắt đầu bằng `cho/E-vmod`, trong khi matcher chỉ chấp nhận `vmod` POS `V/A`.
- **Cải thiện:** Cho phép `E-vmod` nếu từ là `cho` và có `pob` danh hóa phía dưới.

## Kế hoạch cải thiện

### Ưu tiên cao

#### 1. Thay `[0]` bằng cơ chế chấm điểm ứng viên

Source và target nên được xếp hạng theo:

- Frame của trigger.
- POS và dependency label.
- Khoảng cách tới trigger.
- Vị trí trái/phải so với trigger.
- Clause boundary.
- Có phải event predicate hay chỉ là participant/modifier.

Ví dụ với `giúp/khiến/cho_phép + NP-người + VP`, VP phải là event head; NP-người được đưa vào span target như subject/participant nhúng.

#### 2. Thu nhiều complement cùng clause

Thay vì một `target_tok`, thu tập hợp các `dob/obj/vmod/ccomp/xcomp` liên quan, bao gồm `coord/conj`, nhưng dừng tại:

- Dấu chấm phẩy.
- Conjunction bắt đầu mệnh đề độc lập.
- Predicate có subject riêng.
- Trigger nhân quả kế tiếp.

#### 3. Phục hồi source từ ancestor với guard chặt

Chỉ phục hồi parent/ancestor khi:

- Trigger có target rõ.
- Candidate source ở bên trái trong cùng clause.
- Có cấu trúc danh hóa, modal hoặc subject kế thừa đáng tin cậy.
- Không thuộc purpose clause.

### Ưu tiên trung bình

#### 4. Xây dựng frame riêng theo trigger

Tối thiểu nên có frame cho:

- `giúp`
- `khiến`
- `cho_phép`
- `gây/gây_ra`
- `hạn_chế`
- `hỗ_trợ`
- `thúc_đẩy/đẩy_mạnh/tăng_cường`

#### 5. Chuẩn hóa phân đoạn văn bản trước parser

- Loại hoặc tách URL.
- Nhận diện heading.
- Tách bullet/list item.
- Không nối tiêu đề và câu nội dung.
- Tách câu dài có dấu chấm phẩy thành các clause phục vụ extraction.

#### 6. Thêm `collect_clause_span()`

Hàm mới nên hỗ trợ:

- Union sibling có quan hệ phối hợp.
- Loại nhánh trigger khỏi source.
- Giới hạn theo punctuation/clause boundary.
- Dừng khi gặp subject mới hoặc trigger mới.

### Ưu tiên thấp

- Chuẩn hóa trigger đa từ như `gây_ra`, `làm_cho`.
- Gắn modality: question, command, expectation, negation.
- Coreference cho source kiểu `Điều này`.
- Audit bug tiềm ẩn trong `find_triggers()`: `break` sau longest match đang bị comment và cách tính `span_len` đang dùng độ dài ký tự thay vì số token.

## Regression tests cần có

### Nhóm phải tiếp tục đúng

- Dòng 11, 23, 60/78, 75/93, 77, 156, 164, 210, 330.

### Nhóm target beneficiary + event

- Dòng 3, 12, 16, 20, 28, 181, 214, 262.

### Nhóm nhiều kết quả phối hợp

- Dòng 36, 67/85, 119, 121, 145, 149, 188, 191, 235, 302.

### Nhóm source parse sai

- Dòng 18, 128, 137, 187, 233, 236, 275.

### Nhóm matcher bỏ sót

- Dòng 14, 22, 24, 40, 61/79, 63/81, 64/82, 71/89, 76/94, 98, 122, 123, 169, 173, 174, 206, 252.

### Nhóm phải tránh false positive

- Dòng 42, 136, 140, 212, 229, 288.

## Ước lượng tác động

Nếu triển khai lựa chọn target theo frame, thu sibling phối hợp và source recovery có guard:

- Recall matcher Pattern A có thể tăng từ **67,9% lên khoảng 92–96%**.
- Độ đúng hoàn toàn trong các trường hợp đã nhận diện có thể tăng từ **17% lên khoảng 70–82%**.
- Exact-match toàn Pattern A có thể tăng từ **11,5% lên khoảng 58–70%**.

Phần sai số còn lại chủ yếu đến từ phân đoạn câu và dependency parse. Không nên chỉ nới tập dependency label của matcher, vì cách đó có nguy cơ tăng false positive ở purpose clause, câu mệnh lệnh, heading và trigger được dùng như danh từ/trạng thái.

## Kết luận

Điểm mạnh của Pattern A là logic đơn giản, dễ kiểm soát và hoạt động tốt khi dependency parse tạo SVO trực tiếp. Hạn chế lớn nhất không nằm ở việc mở rộng subtree, mà ở quyết định chọn **head ngữ nghĩa** của source/target và việc không mô hình hóa frame riêng của từng trigger.

Thứ tự triển khai khuyến nghị:

1. Chấm điểm target theo trigger frame.
2. Thu các event phối hợp cùng clause.
3. Phục hồi source từ ancestor với guard.
4. Chuẩn hóa sentence/clause segmentation.
5. Bổ sung modality, coreference và chuẩn hóa trigger đa từ.
