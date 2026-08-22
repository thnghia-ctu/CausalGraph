import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pandas as pd

from configs.config import BASE_DIR
from src.normalization.concept_extractor import ConceptExtractor
from src.normalization.state_normalizer import StateNormalizer
from src.utils.text_normalization import normalize_surface, remove_noise_tokens
from evaluate_concept_state_extraction import TEST_SET_PATH, evaluate_extractor

METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_rule_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_rule_predictions.csv"

MODEL_LABEL = "Luật (StateNormalizer + ConceptExtractor)"


def rule_based_adapter():
    state_normalizer = StateNormalizer()
    concept_extractor = ConceptExtractor()

    def run(factor_text: str) -> dict[str, str]:
        normalized = remove_noise_tokens(normalize_surface(factor_text))
        match = state_normalizer.normalize(normalized)
        concept = concept_extractor.extract(normalized, match)
        state_text = normalized[match.span_start:match.span_end] if match else ""
        return {"concept_candidate": concept, "state": state_text}

    return run


def main():
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").fillna("")

    extractor = rule_based_adapter()
    summary, rows = evaluate_extractor(MODEL_LABEL, extractor, df)
    for entry in summary:
        print(entry)

    PREDICTIONS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(PREDICTIONS_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Đã ghi metrics vào {METRICS_OUTPUT_PATH}")
    print(f"Đã ghi dự đoán từng dòng vào {PREDICTIONS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
