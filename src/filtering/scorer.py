from configs.config import KNOWLEDGE_BASE_PATH
from src.utils.helpers import load_xlsx
import src.utils.embedding as emb

class Scorer:
    _instance = None

    def __init__(self, lexicon_embeddings, queries_embeddings):
        self.lexicon_embeddings = lexicon_embeddings
        self.queries_embeddings = queries_embeddings

    @classmethod
    def get_scorer(cls):
        if cls._instance is None:
            lexicons = load_xlsx(KNOWLEDGE_BASE_PATH, 'lexicon', 'lexicon')
            queries = load_xlsx(KNOWLEDGE_BASE_PATH, 'query', 'query')
            cls._instance = cls(
                emb.encode_texts(lexicons),
                emb.encode_texts(queries),
            )
        return cls._instance

    def score(self, item):
        item_embedding = emb.encode_text(item)
        lexicon_score = emb.similarity_from_embedding(
            item_embedding, self.lexicon_embeddings
        )
        queries_score = emb.similarity_from_embedding(
            item_embedding, self.queries_embeddings
        )
        score = 0.3*lexicon_score + 0.7*queries_score
        return score