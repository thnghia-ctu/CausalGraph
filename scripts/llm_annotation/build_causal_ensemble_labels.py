import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR, CAUSAL_SENTENCES_PATH
from src.causal_detection.labeling_prompt import CSV_FIELDS, PROMPT, flatten_batch_result
from src.llm.ensemble_runner import EnsembleRunner
from src.llm.openrouter_client import OpenRouterClient

df = pd.read_csv(CAUSAL_SENTENCES_PATH, sep=";").dropna(subset=["sentence"])

items = [
    {"sentence": row.sentence, "doc_id": row.doc_id, "url": row.url}
    for row in df.itertuples()
]

MAX_BATCHES = 2

runner = EnsembleRunner(
    clients={
        "gemini": OpenRouterClient(model="google/gemini-2.5-flash"),
        "deepseek": OpenRouterClient(model="deepseek/deepseek-v4-flash-0731"),
        "qwen": OpenRouterClient(model="qwen/qwen3.7-flash"),
    },
    items=items,
    prompt=PROMPT,
    flatten_fn=flatten_batch_result,
    fieldnames=CSV_FIELDS,
    agreement_fields=["label"],
    output_dir=BASE_DIR / "data" / "ensemble" / "causal",
    max_batches=MAX_BATCHES,
)

runner.fetch()

print(f"Đã gọi API xong, dữ liệu thô -> {runner.output_dir}")
print("Chạy scripts.causal_classification.aggregate_causal_ensemble_labels để tổng hợp consensus/disagreement.")
