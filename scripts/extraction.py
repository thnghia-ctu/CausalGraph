from pydoc import text

from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.extraction.relation_extractor import RelationExtractor
from src.data_models.dependency_token import parse_dependency_dict 
from src.utils.helpers import load_txt
from pprint import pprint
import pandas as pd
from src.chunking.semantic_chunker import SemanticChunker
from src.filtering.semantic_filter import filter_chunks
from src.utils.helpers import load_txt, save_txt
import traceback
from configs.config import BASE_DIR

# doc = VnCoreNLPParser.parse_file(input_file=input_file, output_file="output/pos.json")
def extract_relations(text):
    sens = VnCoreNLPParser.parse_text(text)
    relation_extractor = RelationExtractor()
    relations = relation_extractor.extract_causal_relation(sens)
    return relations

chunker = SemanticChunker()
extracted_relations={}
for i in range(1, 16):
    try:
        text = load_txt(f"{BASE_DIR}/data/raw/web/{i}_text.txt")
        if not text:
            continue
        chunks = ([chunk.text for chunk in chunker.chunk(text)])
        filtered_chunks, out_filtered_chunks = filter_chunks(chunks)
        filter_text = " ".join(filtered_chunks)
        extracted_relations[i]=extract_relations(filter_text)
    except Exception as e:
        print(f"Error processing file {i}: {e}")
        traceback.print_exc()
        continue

relations_dict = [    
    { 
        "doc_id": i,     
        "pattern": relation["re"].relationship,
        "source": relation["re"].source,
        "trigger": relation["re"].trigger.text,
        "target": relation["re"].target,
        "root": relation["root"],
        "sentence": relation["sen"]
    }
    for i, relations in extracted_relations.items() for relation in relations
]

df = pd.DataFrame(relations_dict)
df.to_csv(f"{BASE_DIR}/output/relations.csv", index=False, encoding="utf-8-sig", header=True)

# # Convert dependency parse to DataFrame
# df = parse_dependency_dict(sens, f"{BASE_DIR}/output/dependency_parse.csv")
# print(df)