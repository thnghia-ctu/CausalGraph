from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=4)
def get_model(model_name: str = DEFAULT_MODEL_NAME) -> object:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def encode_texts(
    texts: Sequence[str],
    model: object | None = None,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    normalize_embeddings: bool = False,
) -> np.ndarray:
    model = model if model is not None else get_model(model_name)
    embeddings = getattr(model, "encode")(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=normalize_embeddings,
    )
    embeddings = np.asarray(embeddings, dtype=float)
    if embeddings.ndim != 2:
        raise ValueError("Embedding model must return a two-dimensional array")
    return embeddings


def encode_text(
    text: str,
    model: object | None = None,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    normalize_embeddings: bool = False,
) -> np.ndarray:
    return encode_texts(
        [text],
        model,
        model_name=model_name,
        normalize_embeddings=normalize_embeddings,
    )[0]


def similarity_from_embedding(
    text_embedding: np.ndarray,
    reference_embeddings: np.ndarray,
    top_k: int = 3,
) -> float:
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if len(reference_embeddings) == 0:
        return 0.0
    scores = cosine_similarity([text_embedding], reference_embeddings)[0]
    return float(np.sort(scores)[-min(top_k, len(scores)):].mean())


def similarity(
    text: str,
    reference_embeddings: np.ndarray,
    model: object | None = None,
    top_k: int = 3,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
) -> float:
    embedding = encode_text(text, model, model_name=model_name)
    return similarity_from_embedding(embedding, reference_embeddings, top_k)
