from src.utils.helpers import  load_txt
from configs.config import BASE_DIR
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.data_models.dependency_token import parse_dependency_dict
import pandas as pd
import re

text=load_txt(f"{BASE_DIR}/input/input.txt").strip()
# text=re.sub(r'\s+', ' ', text)
# text = text.replace("\ufeff", "")
# text = text.replace("_", " ")
# text="Thiếu hạ tầng , thiếu kỹ năng , thiếu nguồn lực và thiếu kết nối thị trường đang khiến họ loay hoay giữa làn sóng công nghệ."
sentences = VnCoreNLPParser.parse_text(text)
parse_dependency_dict(sentences, f"{BASE_DIR}/output/test_out.csv")
extractor = RelationExtractor()
# root=next((token for token in sentences[0].tokens if token.dep == "root"), None)
re=extractor.find_triggers(sentences[0])
ha=extractor.extract_causal_relation(sentences)

# relations = extractor.test(sentences)
df = pd.DataFrame(ha)
df.to_csv(f"{BASE_DIR}/output/test.csv", index=False, encoding="utf-8-sig", header=True)
# print(re)