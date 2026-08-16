import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate
import pandas as pd
from sacrebleu.tokenizers.tokenizer_13a import Tokenizer13a

from configs.config import BASE_DIR, SIMPLIFIER_HF_REPO_ID, SIMPLIFIER_MODEL_DIR
from src.simplification.seq2seq_simplifier import SENTENCE_SEPARATOR, Seq2SeqSimplifier

TEST_SET_PATH = BASE_DIR / "data/eval/simplification_test.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/simplifier_predictions.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/simplifier_metrics.csv"
BATCH_SIZE = 16
BERTSCORE_LANG = "vi"


def load_test_set() -> pd.DataFrame:
    df = pd.read_csv(TEST_SET_PATH, encoding="utf-8-sig").dropna(subset=["sentence", "simple_sentences"])
    return df[df["simple_sentences"].str.strip() != ""]


def load_simplifier() -> Seq2SeqSimplifier:
    local_checkpoint = SIMPLIFIER_MODEL_DIR / "final"
    source = local_checkpoint if local_checkpoint.exists() else SIMPLIFIER_HF_REPO_ID
    return Seq2SeqSimplifier.load(source)


def vi_tokenize(text: str) -> list[str]:
    return Tokenizer13a()(text.lower()).split()


def main():
    df = load_test_set()
    originals = df["sentence"].tolist()
    gold_simples = [s.split(SENTENCE_SEPARATOR) for s in df["simple_sentences"].tolist()]

    simplifier = load_simplifier()
    predicted_simples: list[list[str]] = []
    for i in range(0, len(originals), BATCH_SIZE):
        predicted_simples.extend(simplifier.simplify(originals[i : i + BATCH_SIZE]))

    predictions = [SENTENCE_SEPARATOR.join(p) for p in predicted_simples]
    references = [SENTENCE_SEPARATOR.join(g) for g in gold_simples]
    gold_counts = [len(g) for g in gold_simples]
    predicted_counts = [len(p) for p in predicted_simples]
    count_matches = [gc == pc for gc, pc in zip(gold_counts, predicted_counts)]

    PREDICTIONS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "sentence": originals,
        "gold_simple_sentences": references,
        "predicted_simple_sentences": predictions,
        "gold_count": gold_counts,
        "predicted_count": predicted_counts,
        "count_match": count_matches,
    }).to_csv(PREDICTIONS_OUTPUT_PATH, index=False, encoding="utf-8-sig")

    rouge = evaluate.load("rouge")
    sari = evaluate.load("sari")
    bertscore = evaluate.load("bertscore")

    rouge_result = rouge.compute(predictions=predictions, references=references, tokenizer=vi_tokenize)
    sari_result = sari.compute(sources=originals, predictions=predictions, references=[[r] for r in references])
    bertscore_result = bertscore.compute(predictions=predictions, references=references, lang=BERTSCORE_LANG)

    summary = {
        "Tỷ lệ khớp số lượng câu (%)": round(100 * sum(count_matches) / len(count_matches), 2),
        "ROUGE-1": round(rouge_result["rouge1"], 4),
        "ROUGE-2": round(rouge_result["rouge2"], 4),
        "ROUGE-L": round(rouge_result["rougeL"], 4),
        "SARI": round(sari_result["sari"], 4),
        "BERTScore-P": round(sum(bertscore_result["precision"]) / len(bertscore_result["precision"]), 4),
        "BERTScore-R": round(sum(bertscore_result["recall"]) / len(bertscore_result["recall"]), 4),
        "BERTScore-F1": round(sum(bertscore_result["f1"]) / len(bertscore_result["f1"]), 4),
    }

    for key, value in summary.items():
        print(f"{key}: {value}")
    print(
        "Lưu ý: ROUGE/SARI/BERTScore được tính trên chuỗi đã ghép nhiều câu đơn bằng "
        f"\"{SENTENCE_SEPARATOR}\", nên không đo trực tiếp việc tách câu có đúng ranh giới hay "
        "không (xem Tỷ lệ khớp số lượng câu cho việc đó). SARI đặc biệt được thiết kế cho viết lại "
        "1 câu → 1 câu, áp trên văn bản đã ghép nhiều câu chỉ mang tính tham khảo bổ sung."
    )

    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Đã ghi metrics tổng hợp vào {METRICS_OUTPUT_PATH}")
    print(f"Đã ghi dự đoán từng dòng vào {PREDICTIONS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
