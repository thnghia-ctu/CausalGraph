from configs.config import CHUNK_FILTER_THRESHOLD
from src.filtering.scorer import Scorer


def score_chunks(chunks):
    """Chấm điểm liên quan cho một batch chunk, cùng thứ tự với `chunks`."""
    return Scorer.get_scorer().score(chunks)


def filter_chunks(chunks, threshold=CHUNK_FILTER_THRESHOLD):
    scores = score_chunks(chunks)

    filtered = []
    out_filtered = []
    for chunk, score in zip(chunks, scores):
        (filtered if score > threshold else out_filtered).append(chunk)
    return filtered, out_filtered
