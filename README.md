# CausalGraph
s
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

## Sử dụng

### Thêm lexicon

```bash
python -m scripts.import_lexicon_txt
```

### Cào dữ liệu

```bash
python -m scripts.crawl_data
```
