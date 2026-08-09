# Nhật ký build dữ liệu (data pipeline)

File này ghi lại các bước đã thực hiện để xây dựng dữ liệu thô → chunk đã lọc
→ câu nhân quả yếu, tách riêng khỏi `README.md` (README mô tả cách chạy
chung, file này ghi lại *đã chạy gì, bằng script/cấu hình nào, kết quả ra
sao* — cập nhật dần khi build tiếp). Cập nhật lần gần nhất: 2026-08-09.

Pipeline tổng quan (mỗi bước ghi ra một thư mục trong `data/`):

```
data/links  →  data/raw  →  data/chunks   →  data/causal_sentences  → ...
(thu thập)     (crawl)      (chunk + lọc)     (câu nhân quả yếu)
```

Trạng thái build tính đến 2026-08-09: **Bước 1, 2 đã có dữ liệu, không cần
chạy lại**. **Bước 3, 4 đang chờ rebuild** với các thay đổi mới (xem chi tiết
từng bước) — dữ liệu hiện có trong `data/chunks` và `data/causal_sentences`
là bản cũ, sinh trước các thay đổi ở dưới.

---

## Bước 1 — Thu thập link: `data/links`

**Script**: `python -m scripts.collection.collect_search_links`
**Cấu hình**: `configs/search_sources.py`

- Nguồn tìm kiếm nội bộ (`ENABLED_SEARCH_SOURCES`): `vnexpress`, `nongnghiep`.
- 20 từ khóa tìm kiếm (`SEARCH_KEYWORDS`), xoay quanh "chuyển đổi số nông
  nghiệp" và các biến thể: nông nghiệp số, số hóa nông nghiệp, IoT/AI trong
  nông nghiệp, rào cản/chi phí/hạ tầng chuyển đổi số, chuyển đổi số hợp tác
  xã/sản xuất lúa...
- Tham số: `MAX_PAGES_PER_KEYWORD=10`, `DELAY_SECONDS=2.0`,
  `TIMEOUT_SECONDS=30`.
- Ghi ra `data/links/search_results_raw.csv` (toàn bộ kết quả thô, có thể
  trùng) và `data/links/unique_links.csv` (URL duy nhất, dùng cho bước crawl).

**Trạng thái hiện tại**: đã chạy, chưa cần chạy lại (không đổi từ khóa/nguồn).
`unique_links.csv` có **1.320 URL**.

---

## Bước 2 — Crawl nội dung: `data/raw`

**Script**: `python -m scripts.crawl_data`

- Đọc `data/links/unique_links.csv` (qua `UNIQUE_LINKS_PATH` trong
  `configs/config.py`).
- Gọi `CrawlRunner.crawl_links(links, output_path=BASE_DIR/"data",
  crawler_type="web")` — chỉ crawl loại `web` (không crawl `youtube` trong lần
  build này).
- Mỗi URL → `doc_id` = 12 ký tự đầu của SHA1(url); nội dung text lưu tại
  `data/raw/web/<doc_id>_text.txt`; index tất cả doc tại
  `data/raw/documents.jsonl` (mỗi dòng: `doc_id, url, path, source_type`).
- Có cơ chế resume: nếu `file_path` đã tồn tại thì bỏ qua, không crawl lại.

**Trạng thái hiện tại**: đã chạy, chưa cần chạy lại (không có link mới).
`data/raw/documents.jsonl` có **1.314 document** (1.320 link − 6 lỗi/không lấy
được nội dung).

---

## Bước 3 — Chunk + lọc theo chủ đề: `data/chunks` (bước đang thực hiện)

**Script**: `python -m scripts.chunking.filter_chunks`
(mới di chuyển từ `scripts/filter_chunks.py` → `scripts/chunking/` ngày
2026-08-09 để khớp convention thư mục với `src/chunking/`, tương tự
`scripts/collection/` ↔ `src/collection/`.)

- Đọc `data/raw/documents.jsonl` (`load_documents`).
- `ChunkRunner.chunk_documents(...)`:
  1. Chunk mỗi document bằng `SemanticChunker` (thư viện `chonkie`, model
     `keepitreal/vietnamese-sbert`).
  2. Chấm điểm mỗi chunk theo độ liên quan chủ đề bằng
     `src/filtering/semantic_filter.score_chunks` — điểm = 0.3×khớp lexicon +
     0.7×khớp query, so với ngưỡng `CHUNK_FILTER_THRESHOLD` trong
     `configs/config.py`.
  3. Ghi `data/chunks/chunks_filtered.jsonl` (chunk giữ) và
     `data/chunks/chunks_rejected.jsonl` (chunk loại), mỗi dòng gồm
     `chunk_id, doc_id, url, chunk_index, text`.

### Các điều chỉnh đã áp dụng trước khi chạy build đầy đủ

Xuất phát từ việc kiểm tra định lượng precision/recall của bước lọc này trên
tập nhỏ 17 bài (`output/crawl`), phát hiện 2 nguồn gây mất recall và đã sửa:

1. **`CHUNK_FILTER_THRESHOLD = 0.38`** — giữ nguyên, đã tune trước đó bằng
   hand-label 100 chunk (F1≈0.71). Đã thử hạ ngưỡng, không tốt hơn (kéo theo
   nhiễu, precision rớt còn ~0.51) — không đổi.
2. **Query set trong `configs/knowledge/knowledge_base.xlsx` (sheet
   `query`)**: mở rộng từ 9 → 20 câu. 9 câu gốc chỉ xoay quanh khung "yếu tố
   ảnh hưởng đến quyết định ứng dụng công nghệ số", bỏ sót nội dung đúng chủ
   đề nhưng khác khung (rào cản cụ thể, hiệu quả định lượng, ví dụ công nghệ
   cụ thể — IoT/blockchain/drone, chính sách hỗ trợ, câu chuyện điển hình,
   thống kê kinh tế số vĩ mô). Thêm 11 câu bao phủ các khung này.
3. **`SemanticChunker(min_sentences_per_chunk=2)`** trong
   `src/chunking/semantic_chunker.py` (trước là mặc định `1`) — tránh chunk
   chỉ 1 câu/mảnh câu cụt (vd. "để tinh chế thành sản phẩm dược liệu.") bị
   chấm điểm thấp oan vì thiếu ngữ cảnh, dù nội dung đúng chủ đề.

**Đánh giá định lượng sau khi sửa** (gán nhãn tay toàn bộ 285 chunk của tập
17 bài `output/crawl`, so với nhãn dự đoán của filter):

| | Trước (9 query, min_sent=1) | Sau (20 query, min_sent=2) |
|---|---|---|
| Precision | ~75% | **96.3%** |
| Recall | ~55–65% | **92.4%** |
| F1 | — | **94.3%** |

### Trạng thái hiện tại

`data/chunks/chunks_filtered.jsonl` / `chunks_rejected.jsonl` hiện có **vẫn
là bản build cũ** (từ 29/7, chunking `min_sentences_per_chunk=1`, query set 9
câu — 3.230 kept / 11.870 rejected trên 1.314 document). **Chưa chạy lại**
`scripts.chunking.filter_chunks` trên toàn bộ `data/raw` với cấu hình mới ở
trên.

⚠️ Khi chạy lại: `data/causal_sentences/causal_sentences.csv` (bước sau, đã
có 700 dòng gán tay `human_label`) sẽ lệch `chunk_id` với bản chunk mới —
cần backup/xử lý trước khi build lại bước đó.

---

## Bước 4 — Tách câu nhân quả yếu (weak label): `data/causal_sentences`

**Script**: `python -m scripts.causal_classification.build_causal_sentences`

- Đọc `data/chunks/chunks_filtered.jsonl` (`load_chunks(BASE_DIR/"data")`,
  chỉ đọc chunk đã **giữ** ở Bước 3, không đụng tới `chunks_rejected.jsonl`).
- Với mỗi chunk, `CausalSentenceRunner.process_chunk`
  (`src/causal_detection/causal_sentence_runner.py`):
  1. Tách câu bằng `underthesea.sent_tokenize`.
  2. **Lọc câu ngắn vô nghĩa** (mới thêm 2026-08-09): bỏ câu có
     `word_tokenize(câu) < MIN_TOKENS_PER_SENTENCE (=4)` — loại các câu như số
     mục ("2.4."), tên tác giả/byline ("Thanh Thủy."), heading cụt, trước khi
     đưa vào bước gán nhãn. Đã kiểm chứng trên mẫu thực tế: rác thuần túy rơi
     vào 2–3 token, câu có nghĩa (kể cả câu rất ngắn) đều ≥5 token.
  3. Gán `weak_label` (`causal` / `non_causal`) bằng `TriggerCausalClassifier`
     (`src/causal_detection/trigger_classifier.py`) — so khớp câu (regex,
     không phân biệt hoa thường, có loại trừ ngữ cảnh như "vì" đứng sau "thay")
     với danh sách trigger trong `configs/causal_triggers.xlsx` (**35 trigger**:
     12 `pos`, 14 `neg`, 9 `neu`). Đây là nhãn yếu (distant supervision) để
     bootstrap dữ liệu train, không phải nhãn cuối cùng — xem
     [[causalgraph_causal_sentence_pipeline]].
  4. Ghi mỗi câu ra CSV, kèm trigger khớp đầu tiên (nếu có).
- Ghi ra `data/causal_sentences/causal_sentences.csv` (delimiter `;`,
  `utf-8-sig`, ghi theo từng chunk + flush ngay để chịu được crash giữa
  chừng). Cột: `sentence, weak_label, trigger, chunk_id, doc_id, url,
  sentence_index, human_label` (`human_label` để trống, điền tay sau).

### Trạng thái hiện tại

`data/causal_sentences/causal_sentences.csv` hiện có **vẫn là bản build cũ**
(ghi lúc 03/8, từ `data/chunks` cũ — trước cả 3 thay đổi ở Bước 3 lẫn bộ lọc
câu ngắn ở Bước 4): **9.759 câu** (7.764 `non_causal` / 1.995 `causal` theo
weak_label), thêm 2 cột `svm_label`/`fasttext_label` do 2 script riêng
(`scripts/causal_classification/label_by_embedding.py`,
`label_by_fasttext.py`) bồi vào sau, và **700/9.759 dòng đã gán tay
`human_label`**. **Chưa chạy lại** bước này.

⚠️ Rebuild Bước 3 xong mới nên rebuild bước này — nhưng ghi đè sẽ **mất
700 dòng `human_label`** đã gán tay (script mở file ở mode `"w"`, không merge
với bản cũ). Cần tự backup (hoặc merge lại theo `sentence`/`chunk_id`) trước
khi chạy lại, không tự động giữ được.

---

## Bước tiếp theo (chưa build, chưa viết tài liệu chi tiết)

`scripts/causal_classification/label_by_embedding.py` và `label_by_fasttext.py`
— bồi thêm cột `svm_label`/`fasttext_label` vào chính
`data/causal_sentences/causal_sentences.csv` để so sánh với `weak_label`.
`scripts/llm_annotation/build_causal_ensemble_labels.py` — gán nhãn bằng
ensemble LLM (đã chạy pilot ~28 câu tại `data/ensemble/causal_pilot/`).
