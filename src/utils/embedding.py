from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

_model = None


def get_model(model_name="all-MiniLM-L6-v2"):
    global _model

    if _model is None:
        _model = SentenceTransformer(model_name)

    return _model


def encode_text(text, model=None):
    if model is None:
        model = get_model()

    return model.encode(
        text,
        convert_to_numpy=True
    )


def encode_texts(texts, model=None):
    if model is None:
        model = get_model()

    return model.encode(
        texts,
        convert_to_numpy=True
    )


def similarity_from_embedding(
    text_embedding,
    reference_embeddings,
    top_k=3
):
    if len(reference_embeddings) == 0:
        return 0.0

    sims = cosine_similarity(
        [text_embedding],
        reference_embeddings
    )[0]

    k = min(top_k, len(sims))

    return float(
        np.sort(sims)[-k:].mean()
    )


def similarity(
    text,
    reference_embeddings,
    model=None,
    top_k=3
):
    text_embedding = encode_text(
        text,
        model
    )

    return similarity_from_embedding(
        text_embedding,
        reference_embeddings,
        top_k
    )