from configs.config import BASE_DIR
from src.utils.helpers import load_xlsx
from src.utils.embedding import encode_texts
from src.filtering.scorer import Scorer


def filter_chunks(chunks, threshold=0.55):
    knowledge_base_path = BASE_DIR / "configs/knowledge/knowledge_base.xlsx"

    lexicons = load_xlsx(knowledge_base_path, 'lexicon', 'lexicon')
    lexicon_embeddings = encode_texts(lexicons)
    
    queries = load_xlsx(knowledge_base_path, 'query', 'query')
    queries_embeddings = encode_texts(queries)
    
    scorer = Scorer(lexicon_embeddings, queries_embeddings)

    filtered = []
    out_filtered = []

    for chunk in chunks:
        if scorer.score(chunk) > threshold:
            filtered.append(chunk)
        else:
            out_filtered.append(chunk)
    return filtered, out_filtered
