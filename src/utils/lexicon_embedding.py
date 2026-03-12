from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class LexiconEmbedding:

    def __init__(self, terms, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.terms = terms
        self.embeddings = self.model.encode(terms)

    def similarity(self, text):
        text_emb = self.model.encode([text])
        sim = cosine_similarity(text_emb, self.embeddings)
        return sim.max()

    def is_relevant(self, text, threshold=0.6):
        return self.similarity(text) >= threshold