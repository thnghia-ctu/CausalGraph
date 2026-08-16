import sys
from collections import Counter
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import BASE_DIR, CONCEPT_STATE_TAGGER_HF_REPO_ID, CONCEPT_STATE_TAGGER_MODEL_DIR
from src.extraction.phobert_bio_tagger import words_and_offsets
from src.extraction.phobert_concept_state_tagger import PhoBertConceptStateTagger

TEST_SET_PATH = BASE_DIR / "data/eval/concept_state_test.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/concept_state_extraction_predictions.csv"
ROLES = ("concept_candidate", "state")
Extractor = Callable[[str], dict[str, str]]
EMPTY_RESULT = {"concept_candidate": "", "state": ""}


def load_phobert() -> PhoBertConceptStateTagger:
    local_checkpoint = CONCEPT_STATE_TAGGER_MODEL_DIR / "final"
    source = local_checkpoint if local_checkpoint.exists() else CONCEPT_STATE_TAGGER_HF_REPO_ID
    return PhoBertConceptStateTagger.load(source)


def phobert_adapter(tagger: PhoBertConceptStateTagger) -> Extractor:
    def run(text: str) -> dict[str, str]:
        result = tagger.extract(text)
        if result is None:
            return dict(EMPTY_RESULT)
        return {
            "concept_candidate": result.concept_candidate.text if result.concept_candidate else "",
            "state": result.state or "",
        }

    return run


def tokenize(text: str) -> list[str]:
    return words_and_offsets(text.replace("_", " "))[0] if text.strip() else []


def evaluate_extractor(name: str, predict: Extractor, df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    counts = {role: {"tp": 0, "fp": 0, "fn": 0} for role in ROLES}
    partial_scores: dict[str, list[float]] = {role: [] for role in ROLES}
    micro_overlap = {role: [0, 0, 0] for role in ROLES}
    rows = []

    for factor_text, gold_concept, gold_state in zip(df["factor_text"], df["concept_candidate"], df["state"]):
        pred_texts = predict(factor_text)
        gold_texts = {"concept_candidate": gold_concept, "state": gold_state}

        row = {"model": name, "factor_text": factor_text}
        row_exact = True
        for role in ROLES:
            gold_tokens = tokenize(gold_texts[role])
            pred_tokens = tokenize(pred_texts[role])

            if gold_tokens and pred_tokens:
                if gold_tokens == pred_tokens:
                    counts[role]["tp"] += 1
                else:
                    counts[role]["fp"] += 1
                    counts[role]["fn"] += 1
                    row_exact = False
            elif pred_tokens:
                counts[role]["fp"] += 1
                row_exact = False
            elif gold_tokens:
                counts[role]["fn"] += 1
                row_exact = False

            if gold_tokens or pred_tokens:
                overlap = sum((Counter(gold_tokens) & Counter(pred_tokens)).values())
                partial_scores[role].append(2 * overlap / (len(gold_tokens) + len(pred_tokens)))
                micro_overlap[role][0] += overlap
                micro_overlap[role][1] += len(gold_tokens)
                micro_overlap[role][2] += len(pred_tokens)

            row[f"gold_{role}"] = gold_texts[role]
            row[f"pred_{role}"] = " ".join(pred_tokens).replace("_", " ")

        row["exact_match"] = row_exact
        rows.append(row)

    summary = []
    for role in ROLES:
        tp, fp, fn = counts[role]["tp"], counts[role]["fp"], counts[role]["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        exact_f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        overlap, gold_len, pred_len = micro_overlap[role]
        token_precision = overlap / pred_len if pred_len else 0.0
        token_recall = overlap / gold_len if gold_len else 0.0
        token_f1 = 2 * token_precision * token_recall / (token_precision + token_recall) if (token_precision + token_recall) else 0.0

        partial_f1 = sum(partial_scores[role]) / len(partial_scores[role]) if partial_scores[role] else 0.0

        summary.append({
            "Mô hình": name,
            "Vai trò": role.upper(),
            "Precision (entity exact)": round(precision, 4),
            "Recall (entity exact)": round(recall, 4),
            "Entity exact F1": round(exact_f1, 4),
            "Token-level F1": round(token_f1, 4),
            "Entity partial F1": round(partial_f1, 4),
            "Support": tp + fn,
        })

    exact_match_rate = sum(r["exact_match"] for r in rows) / len(rows)
    summary.append({
        "Mô hình": name,
        "Vai trò": "Exact-pair match (%)",
        "Precision (entity exact)": "",
        "Recall (entity exact)": "",
        "Entity exact F1": round(100 * exact_match_rate, 2),
        "Token-level F1": "",
        "Entity partial F1": "",
        "Support": len(rows),
    })

    return summary, rows


def main():
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").fillna("")

    phobert = load_phobert()

    extractors: dict[str, Extractor] = {
        "PhoBERT": phobert_adapter(phobert),
    }

    all_summary_rows, all_prediction_rows = [], []
    for name, predict in extractors.items():
        summary, rows = evaluate_extractor(name, predict, df)
        print(f"=== {name} ===")
        for entry in summary:
            print(entry)
        all_summary_rows.extend(summary)
        all_prediction_rows.extend(rows)

    PREDICTIONS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_prediction_rows).to_csv(PREDICTIONS_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_summary_rows).to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Đã ghi metrics tổng hợp vào {METRICS_OUTPUT_PATH}")
    print(f"Đã ghi dự đoán từng dòng vào {PREDICTIONS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
