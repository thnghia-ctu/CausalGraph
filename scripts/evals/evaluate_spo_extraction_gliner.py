import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import pandas as pd
from gliner import GLiNER

from configs.config import BASE_DIR
from evaluate_spo_extraction import TEST_SET_PATH, evaluate_extractor

DEFAULT_MODEL = "urchade/gliner_multi-v2.1"
MODEL_LABEL_TEMPLATE = "GLiNER zero-shot ({model})"

LABEL_SUBJECT = "cause: the factor, action or condition that produces an effect"
LABEL_PREDICATE = "causal connector: a word or phrase expressing a cause-effect relationship, e.g. cause, lead to, help, result in, because, due to"
LABEL_OBJECT = "effect: the outcome or result produced by the cause"
LABELS = [LABEL_SUBJECT, LABEL_PREDICATE, LABEL_OBJECT]

METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/spo_extraction_gliner_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/spo_extraction_gliner_predictions.csv"


def best_span_per_label(entities: list[dict], label: str) -> str:
    candidates = [e for e in entities if e["label"] == label]
    if not candidates:
        return ""
    return max(candidates, key=lambda e: e["score"])["text"]


def gliner_adapter(model: GLiNER, threshold: float):
    def run(text: str) -> dict[str, str]:
        entities = model.predict_entities(text, LABELS, threshold=threshold)
        return {
            "subject": best_span_per_label(entities, LABEL_SUBJECT),
            "predicate": best_span_per_label(entities, LABEL_PREDICATE),
            "object": best_span_per_label(entities, LABEL_OBJECT),
        }

    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF repo id của checkpoint GLiNER đa ngôn ngữ")
    parser.add_argument("--threshold", type=float, default=0.1, help="Ngưỡng confidence khi predict_entities")
    args = parser.parse_args()

    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").fillna("")

    print(f"Đang tải GLiNER checkpoint {args.model}...")
    model = GLiNER.from_pretrained(args.model)

    extractor = gliner_adapter(model, args.threshold)
    model_label = MODEL_LABEL_TEMPLATE.format(model=args.model)

    summary, rows = evaluate_extractor(model_label, extractor, df)
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
