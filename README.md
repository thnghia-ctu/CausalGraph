# Cài thư viện
pip install -r requirements.txt

git clone https://github.com/nlp-uoregon/trankit.git
cd trankit
pip install -e .

# Script thêm lexicon
python -m scripts.import_lexicon_txt

# Script cào dữ liệu
python -m scripts.crawl_data