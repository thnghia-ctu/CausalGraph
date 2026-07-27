from src.filtering.scorer import Scorer


def filter_chunks(chunks, threshold=0.55):
    scorer = Scorer.get_scorer()

    filtered = []
    out_filtered = []

    for chunk in chunks:
        if scorer.score(chunk) > threshold:
            filtered.append(chunk)
        else:
            out_filtered.append(chunk)
    return filtered, out_filtered
