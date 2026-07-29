# CausalGraph

## Yêu cầu hệ thống

Trước khi cài đặt, hãy bảo đảm máy đã có:

- Python 3.12 (khuyến nghị để tương thích ổn định với các thư viện trong dự án).
- `pip` đi kèm với Python.
- Java JDK 17 (cần cho `py_vncorenlp`).
- Miniconda (không bắt buộc, nhưng được khuyến nghị để quản lý môi trường Python).

Kiểm tra các công cụ đã cài đặt:

```bash
python --version
pip --version
java -version
conda --version
```
## Cài đặt với Conda

```bash
conda create --name causalgraph python=3.12
conda activate causalgraph
conda install --channel conda-forge openjdk=17
pip install -r requirements.txt
pip install google-genai
python -m scripts.download_vncorenlp
```

Lệnh trên cài Java 17 riêng trong môi trường `causalgraph`, không thay đổi Java
của hệ thống. Kiểm tra Java sau khi cài:

```bash
java -version
which java       # Linux/macOS
where java       # Windows
```

## Quy trình xử lý dữ liệu

### 1. Thu thập link bài viết

```bash
python -m scripts.collection.collect_search_links
```

Tìm kiếm theo từ khóa khai báo trong `configs/search_sources.py`, ghi kết quả
vào `data/links/search_results_raw.csv` và `data/links/unique_links.csv`.

### 2. Cào nội dung bài viết

```bash
python -m scripts.crawl_data
```

Đọc URL từ `data/links/unique_links.csv`, cào nội dung và lưu text vào
`data/raw/web/`, đồng thời ghi ánh xạ URL ↔ file vào `data/raw/manifest.jsonl`.

### 3. Lọc chunk theo độ liên quan

```bash
python -m scripts.filter_chunks
```

Đọc `data/raw/manifest.jsonl`, chia nhỏ (chunk) từng bài viết rồi lọc theo độ
tương đồng ngữ nghĩa với lexicon/query. Kết quả:
- `data/chunks/chunks_filtered.jsonl` — chunk được giữ lại, map tới `url`/`doc_id` gốc.
- `data/chunks/chunks_rejected.jsonl` — chunk bị loại.
