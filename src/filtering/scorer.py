import src.utils.embedding as emb

class Scorer:
    def __init__(self, lexicon_embeddings, queries_embeddings):
        self.lexicon_embeddings = lexicon_embeddings
        self.queries_embeddings = queries_embeddings

    def score(self, item):
        item_embedding = emb.encode_text(item)
        lexicon_score = emb.similarity_from_embedding(
            item_embedding, self.lexicon_embeddings
        )
        queries_score = emb.similarity_from_embedding(
            item_embedding, self.queries_embeddings
        )
        score = 2 * (lexicon_score * queries_score) / (lexicon_score + queries_score) if lexicon_score + queries_score != 0 else 0
        return score