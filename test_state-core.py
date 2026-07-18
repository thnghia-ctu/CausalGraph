from src.utils.helpers import  load_txt
from configs.config import BASE_DIR
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.data_models.dependency_token import parse_dependency_dict
import pandas as pd
import re
from src.normalization.factor_parser import FactorParser
from src.normalization.state_normalizer import StateNormalizer

state_normalizer = StateNormalizer()
factor_parser = FactorParser(state_normalizer=state_normalizer)
text=load_txt(f"{BASE_DIR}/input/pattern_optimization_test_sentences.txt").strip()
text=re.sub(r'\s+', ' ', text)
text = text.replace("\ufeff", "")
text = text.replace("_", " ")
sentences = VnCoreNLPParser.parse_text(text)
# parse_dependency_dict(sentences, f"{BASE_DIR}/output/test_out.csv")
extractor = RelationExtractor()
re = extractor.extract_causal_relation(sentences)
flatten_relations=[]
for relation in re:
    source = relation["re"].source
    target = relation["re"].target
    source_concept = factor_parser.parse(source.text) if source else None
    target_concept = factor_parser.parse(target.text) if target else None
    if source is not None or target is not None:
        flatten_relations.append(
        {
            "source": source.text if source else None,
            "source_state": source_concept.state if source_concept else None,
            "source_core": source_concept.factor_core if source_concept else None,
            "target": target.text if target else None,
            "target_state": target_concept.state if target_concept else None,
            "target_core": target_concept.factor_core if target_concept else None,
            "sentence": relation["sen"]
        }
    )
df = pd.DataFrame(flatten_relations)
df.to_csv(f"{BASE_DIR}/output/test-haha.csv", index=False, encoding="utf-8-sig", header=True)