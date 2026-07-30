import pandas as pd

from configs.config import CAUSAL_SENTENCES_PATH, LLM_RELATIONS_PATH
from src.llm.batch_processor import BatchProcessor
from src.llm.gemini_client import GeminiClient

df = pd.read_csv(CAUSAL_SENTENCES_PATH)
causal_df = df[df["weak_label"] == "causal"].dropna(subset=["sentence"])

if LLM_RELATIONS_PATH.exists():
    processed_df = pd.read_csv(LLM_RELATIONS_PATH)
    processed_pairs = set(zip(processed_df["doc_id"], processed_df["original_sentence"]))
    causal_df = causal_df[
        ~pd.Series(zip(causal_df["doc_id"], causal_df["sentence"]), index=causal_df.index).isin(
            processed_pairs
        )
    ]

items = [
    {"sentence": row.sentence, "doc_id": row.doc_id, "url": row.url}
    for row in causal_df.itertuples()
]

MAX_BATCHES = None  # đặt số nguyên (vd: 3) để chạy thử trước khi chạy toàn bộ

bp = BatchProcessor(
    llm=GeminiClient(),
    items=items,
    output_path=LLM_RELATIONS_PATH,
    max_batches=MAX_BATCHES,
)

bp.process_batches()