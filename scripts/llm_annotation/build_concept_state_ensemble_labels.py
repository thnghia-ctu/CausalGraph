import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR, SIMPLIFICATION_SPO_PATH
from src.llm.ensemble_runner import EnsembleRunner
from src.llm.openrouter_client import OpenRouterClient
from src.simplification.concept_state_annotation_prompt import (
    CSV_FIELDS,
    PROMPT,
    concept_state_agree,
    flatten_batch_result,
)

PRIMARY_MODEL = "google/gemini-2.5-flash"
OUTPUT_DIR = BASE_DIR / "data" / "ensemble" / "concept_state"


def build_items() -> list[dict[str, str]]:
    df = pd.read_csv(SIMPLIFICATION_SPO_PATH, encoding="utf-8-sig")
    factors = pd.concat([df["subject_text"], df["object_text"]]).dropna().str.strip()
    factors = factors[factors != ""].drop_duplicates()
    return [{"item_id": str(index), "sentence": text} for index, text in enumerate(factors)]


def main() -> None:
    items = build_items()
    print(f"{len(items)} factor_text duy nhất (từ subject_text + object_text).")

    runner = EnsembleRunner(
        clients={
            "pass1": OpenRouterClient(model=PRIMARY_MODEL),
            "pass2": OpenRouterClient(model=PRIMARY_MODEL),
        },
        items=items,
        prompt=PROMPT,
        flatten_fn=flatten_batch_result,
        fieldnames=CSV_FIELDS,
        agreement_fn=concept_state_agree,
        output_dir=OUTPUT_DIR,
    )
    consensus_rows, disagreement_rows = runner.run()

    print(f"Đồng thuận: {len(consensus_rows)} -> {OUTPUT_DIR / 'consensus.csv'}")
    print(f"Cần review (bất đồng hoặc grounding fail): {len(disagreement_rows)} -> {OUTPUT_DIR / 'disagreement.csv'}")


if __name__ == "__main__":
    main()
