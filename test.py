from src.utils.helpers import  load_txt
from configs.config import BASE_DIR
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.data_models.dependency_token import parse_dependency_dict

import pandas as pd
import re

# text=load_txt(f"{BASE_DIR}/input/nead_refactor_cases.txt").strip()
text = "Hạ_tầng công_nghệ_thông_tin ở vùng_sâu , vùng_xa còn yếu , tỷ_lệ phủ_sóng Internet chưa ổn_định , gây khó_khăn khi triển_khai phần_mềm và thiết_bị IoT ."
text=re.sub(r'\s+', ' ', text)
text = text.replace("\ufeff", "")
text = text.replace("_", " ")
# text="Thiếu hạ tầng , thiếu kỹ năng , thiếu nguồn lực và thiếu kết nối thị trường đang khiến họ loay hoay giữa làn sóng công nghệ."
sentences = VnCoreNLPParser.parse_text(text)
parse_dependency_dict(sentences, f"{BASE_DIR}/output/test_out.csv")
extractor = RelationExtractor()
# root=next((token for token in sentences[0].tokens if token.dep == "root"), None)
re=extractor.extract_causal_relation(sentences)
flatten_relations = [
    {
        "source": relation["re"].source.text
        if relation["re"].source else None,
        "trigger": relation["re"].trigger.text,
        "target": relation["re"].target.text
        if relation["re"].target else None,
        "root_re": relation["root_re"],
        "sentence": relation["sen"],
    }
    for relation in re
]
# relations = extractor.test(sentences)
df = pd.DataFrame(flatten_relations)
df.to_csv(f"{BASE_DIR}/output/test1.csv", index=False, encoding="utf-8-sig", header=True)
# print(re)
