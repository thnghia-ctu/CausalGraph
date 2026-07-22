import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR
from src.pipeline import Pipeline
import src.utils.helpers as hlp
from src.concept_builder.candidate_inventory import build_candidate_counts
from src.concept_builder.candidate_neighbors import build_candidate_review_queue


MAX_CANDIDATE_LENGTH = 200
SEED_LIMIT = 1000
TOP_K = 5

CANDIDATES_PATH = f"{BASE_DIR}/output/large_candidates.csv"
COUNTS_PATH = f"{BASE_DIR}/input/counted_candidates.csv"
REVIEW_PATH = f"{BASE_DIR}/input/candidate_review_queue.xlsx"


def build_inventory():
    pipeline = Pipeline()
    candidates = pipeline.run(MAX_CANDIDATE_LENGTH)
    if not candidates:
        raise RuntimeError("Pipeline không tạo được candidate. File cũ được giữ nguyên.")

    hlp.save_to_csv(
        CANDIDATES_PATH,
        data={"concept_candidate": candidates},
    )

    return build_candidate_counts(
        CANDIDATES_PATH,
        COUNTS_PATH,
        candidate_columns=["concept_candidate"],
    )


def build_review():
    candidate_counts = pd.read_csv(COUNTS_PATH, encoding="utf-8-sig")
    if candidate_counts.empty:
        raise RuntimeError("counted_candidates.csv đang rỗng.")

    review_queue = build_candidate_review_queue(
        candidate_counts,
        seed_limit=SEED_LIMIT,
        top_k=TOP_K,
    )
    if review_queue.empty:
        raise RuntimeError("Không tạo được candidate review queue.")

    review_queue.to_excel(
        REVIEW_PATH,
        sheet_name="candidate_neighbors",
        index=False,
    )
    return review_queue


def main():
    build_review()


if __name__ == "__main__":
    main()
