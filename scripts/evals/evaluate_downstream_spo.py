import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import (
    BASE_DIR,
    SIMPLIFIER_VARIANTS,
    SPO_TAGGER_HF_REPO_ID,
    SPO_TAGGER_MODEL_DIR,
)
from src.extraction.phobert_bio_tagger import words_and_offsets
from src.extraction.phobert_spo_tagger import PhoBertSpoTagger
from src.simplification.seq2seq_simplifier import SENTENCE_SEPARATOR, Seq2SeqSimplifier

SIMP_TEST_PATH = BASE_DIR / "data/eval/simplification_test.csv"
SPO_TEST_PATH = BASE_DIR / "data/eval/spo_test.csv"
LLM_RAW_DIR = BASE_DIR / "output/evals/llm_raw"
GPT_PREDICTIONS_PATH = BASE_DIR / "output/evals/simplifier_predictions_gpt.csv"
METRICS_OUTPUT_PATH = BASE_DIR / "output/evals/downstream_spo_metrics.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "output/evals/downstream_spo_predictions.csv"

OVERLAP_THRESHOLD = 0.5
BATCH_SIZE = 16


def tokenize(text: str) -> list[str]:
    """Tách từ tiếng Việt qua PhoBERT tokenizer/underthesea và bỏ ký tự nối underscore."""
    return words_and_offsets(text.replace("_", " "))[0] if text.strip() else []


def span_dice(tokens1: list[str], tokens2: list[str]) -> float:
    """Hệ số Dice đo độ chồng lấp token giữa hai span: 2|A & B| / (|A| + |B|)."""
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    overlap = sum((Counter(tokens1) & Counter(tokens2)).values())
    return 2.0 * overlap / (len(tokens1) + len(tokens2))


def triple_similarity(t_pred: dict[str, str], t_gold: dict[str, str]) -> tuple[bool, float]:
    """So sánh 2 bộ ba quan hệ: trả về (exact_match, overlap_score)."""
    s_p, s_g = tokenize(t_pred.get("subject", "")), tokenize(t_gold.get("subject", ""))
    p_p, p_g = tokenize(t_pred.get("predicate", "")), tokenize(t_gold.get("predicate", ""))
    o_p, o_g = tokenize(t_pred.get("object", "")), tokenize(t_gold.get("object", ""))

    exact = (s_p == s_g) and (p_p == p_g) and (o_p == o_g)
    dice_s = span_dice(s_p, s_g)
    dice_p = span_dice(p_p, p_g)
    dice_o = span_dice(o_p, o_g)
    avg_dice = (dice_s + dice_p + dice_o) / 3.0
    return exact, avg_dice


def match_triples(
    pred_triples: list[dict[str, str]],
    gold_triples: list[dict[str, str]],
    threshold: float = OVERLAP_THRESHOLD,
) -> dict[str, Any]:
    """So khớp tham lam (Greedy Bipartite Matching) giữa tập bộ ba dự đoán và gold trên 1 câu phức."""
    if not pred_triples and not gold_triples:
        return {
            "tp_exact": 0,
            "fp_exact": 0,
            "fn_exact": 0,
            "tp_partial": 0,
            "fp_partial": 0,
            "fn_partial": 0,
            "exact_sentence": True,
            "overlap_scores": [],
        }

    pairs: list[tuple[float, bool, int, int]] = []
    for i, p in enumerate(pred_triples):
        for j, g in enumerate(gold_triples):
            exact, score = triple_similarity(p, g)
            pairs.append((score, exact, i, j))

    # Ưu tiên match exact trước, sau đó theo điểm overlap cao nhất
    pairs.sort(key=lambda x: (x[1], x[0]), reverse=True)

    used_p, used_g = set(), set()
    tp_exact, tp_partial = 0, 0
    scores: list[float] = []

    for score, exact, i, j in pairs:
        if i not in used_p and j not in used_g:
            used_p.add(i)
            used_g.add(j)
            if exact:
                tp_exact += 1
            if score >= threshold:
                tp_partial += 1
            scores.append(score)

    fp_exact = len(pred_triples) - tp_exact
    fn_exact = len(gold_triples) - tp_exact
    fp_partial = len(pred_triples) - tp_partial
    fn_partial = len(gold_triples) - tp_partial
    exact_sent = (len(pred_triples) == len(gold_triples) == tp_exact)

    return {
        "tp_exact": tp_exact,
        "fp_exact": fp_exact,
        "fn_exact": fn_exact,
        "tp_partial": tp_partial,
        "fp_partial": fp_partial,
        "fn_partial": fn_partial,
        "exact_sentence": exact_sent,
        "overlap_scores": scores,
    }


def load_datasets() -> tuple[pd.DataFrame, dict[int, list[dict[str, str]]]]:
    """Tải tập 182 câu phức và gom 361 quan hệ SPO gold theo ID."""
    df_simp = pd.read_csv(SIMP_TEST_PATH, encoding="utf-8-sig")
    df_spo = pd.read_csv(SPO_TEST_PATH, encoding="utf-8-sig").fillna("")

    gold_by_id: dict[int, list[dict[str, str]]] = {int(i): [] for i in df_simp["id"]}
    for _, row in df_spo.iterrows():
        item_id = int(row["id"])
        s = str(row["subject_text"]).strip()
        p = str(row["predicate"]).strip()
        o = str(row["object_text"]).strip()
        if s or o:
            gold_by_id[item_id].append({"subject": s, "predicate": p, "object": o})

    return df_simp, gold_by_id


def load_gpt_simples(df_simp: pd.DataFrame) -> dict[int, list[str]]:
    """Tải câu đơn đã tách sẵn bởi gpt-4.1-mini (output/evals/simplifier_predictions_gpt.csv),
    không gọi lại API. Khớp theo thứ tự với df_simp, có kiểm tra để tránh lệch hàng."""
    gpt_df = pd.read_csv(GPT_PREDICTIONS_PATH, encoding="utf-8-sig")
    if len(gpt_df) != len(df_simp) or not (gpt_df["sentence"].values == df_simp["sentence"].values).all():
        raise ValueError(
            f"{GPT_PREDICTIONS_PATH} không khớp thứ tự/nội dung với {SIMP_TEST_PATH} -- "
            "chạy lại scripts/evals/evaluate_simplifier_llm.py --model gpt trước."
        )
    return {
        int(row_id): gpt_df.iloc[i]["predicted_simple_sentences"].split(SENTENCE_SEPARATOR)
        for i, row_id in enumerate(df_simp["id"])
    }


def load_spo_tagger() -> PhoBertSpoTagger:
    local_checkpoint = SPO_TAGGER_MODEL_DIR / "final"
    source = local_checkpoint if local_checkpoint.exists() else SPO_TAGGER_HF_REPO_ID
    return PhoBertSpoTagger.load(source)


def extract_triples_from_texts(texts: list[str], tagger: PhoBertSpoTagger) -> list[dict[str, str]]:
    """Trích xuất danh sách SPO từ một danh sách các câu đơn (hoặc 1 câu phức)."""
    triples = []
    for t in texts:
        t = t.strip()
        if not t:
            continue
        res = tagger.extract(t)
        if res is not None:
            s = res.subject.text if res.subject else ""
            p = res.predicate or ""
            o = res.object.text if res.object else ""
            if s or o:
                triples.append({"subject": s, "predicate": p, "object": o})
    return triples


def evaluate_pipeline(
    pipeline_name: str,
    predictions_by_id: dict[int, list[dict[str, str]]],
    gold_by_id: dict[int, list[dict[str, str]]],
    df_simp: pd.DataFrame,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Tính toán toàn bộ chỉ số đánh giá cho một pipeline."""
    tot_tp_exact = tot_fp_exact = tot_fn_exact = 0
    tot_tp_partial = tot_fp_partial = tot_fn_partial = 0
    exact_sentence_count = 0
    all_scores: list[float] = []
    pred_rows: list[dict[str, Any]] = []

    for _, row in df_simp.iterrows():
        item_id = int(row["id"])
        sentence = row["sentence"]
        golds = gold_by_id.get(item_id, [])
        preds = predictions_by_id.get(item_id, [])

        res = match_triples(preds, golds)
        tot_tp_exact += res["tp_exact"]
        tot_fp_exact += res["fp_exact"]
        tot_fn_exact += res["fn_exact"]

        tot_tp_partial += res["tp_partial"]
        tot_fp_partial += res["fp_partial"]
        tot_fn_partial += res["fn_partial"]

        if res["exact_sentence"]:
            exact_sentence_count += 1
        all_scores.extend(res["overlap_scores"])

        pred_rows.append({
            "pipeline": pipeline_name,
            "id": item_id,
            "sentence": sentence,
            "num_gold_triples": len(golds),
            "num_pred_triples": len(preds),
            "gold_triples": json.dumps(golds, ensure_ascii=False),
            "pred_triples": json.dumps(preds, ensure_ascii=False),
            "tp_exact": res["tp_exact"],
            "exact_sentence_match": res["exact_sentence"],
        })

    # Exact Metrics
    prec_ex = tot_tp_exact / (tot_tp_exact + tot_fp_exact) if (tot_tp_exact + tot_fp_exact) else 0.0
    rec_ex = tot_tp_exact / (tot_tp_exact + tot_fn_exact) if (tot_tp_exact + tot_fn_exact) else 0.0
    f1_ex = 2 * prec_ex * rec_ex / (prec_ex + rec_ex) if (prec_ex + rec_ex) else 0.0

    # Partial Metrics
    prec_pt = tot_tp_partial / (tot_tp_partial + tot_fp_partial) if (tot_tp_partial + tot_fp_partial) else 0.0
    rec_pt = tot_tp_partial / (tot_tp_partial + tot_fn_partial) if (tot_tp_partial + tot_fn_partial) else 0.0
    f1_pt = 2 * prec_pt * rec_pt / (prec_pt + rec_pt) if (prec_pt + rec_pt) else 0.0

    mean_dice = sum(all_scores) / len(all_scores) if all_scores else 0.0
    sentence_exact_rate = exact_sentence_count / len(df_simp) * 100.0

    summary = {
        "Pipeline": pipeline_name,
        "Precision (Exact)": round(prec_ex, 4),
        "Recall (Exact)": round(rec_ex, 4),
        "F1 (Exact)": round(f1_ex, 4),
        "Precision (Partial)": round(prec_pt, 4),
        "Recall (Partial)": round(rec_pt, 4),
        "F1 (Partial)": round(f1_pt, 4),
        "Mean Triple Dice": round(mean_dice, 4),
        "Sentence Exact Match (%)": round(sentence_exact_rate, 2),
        "Total Pred Triples": tot_tp_exact + tot_fp_exact,
        "Total Gold Triples": tot_tp_exact + tot_fn_exact,
    }
    return summary, pred_rows


def run_evaluations(args: argparse.Namespace):
    df_simp, gold_by_id = load_datasets()
    spo_tagger = load_spo_tagger()

    print(f"Đã tải {len(df_simp)} câu phức và {sum(len(g) for g in gold_by_id.values())} bộ ba SPO gold.")

    all_summaries: list[dict[str, Any]] = []
    all_pred_rows: list[dict[str, Any]] = []

    # 1. Baseline: Raw Complex (Không tách câu)
    print("\n[1/4] Đang đánh giá Pipeline 1: Raw Complex (Không tách câu)...")
    preds_raw: dict[int, list[dict[str, str]]] = {}
    for _, row in df_simp.iterrows():
        item_id = int(row["id"])
        sentence = row["sentence"]
        preds_raw[item_id] = extract_triples_from_texts([sentence], spo_tagger)

    summary_raw, rows_raw = evaluate_pipeline("1. Raw Complex (Không tách)", preds_raw, gold_by_id, df_simp)
    all_summaries.append(summary_raw)
    all_pred_rows.extend(rows_raw)

    # 2. Pipeline đề xuất: ViT5 + PhoBERT-SPO
    simplifier_key = args.model
    print(f"\n[2/4] Đang đánh giá Pipeline 2: {simplifier_key.upper()} Simplifier + PhoBERT-SPO...")
    variant = SIMPLIFIER_VARIANTS.get(simplifier_key, SIMPLIFIER_VARIANTS["vit5"])
    local_simplifier = variant["model_dir"] / "final"
    source = local_simplifier if local_simplifier.exists() else variant["hf_repo_id"]
    simplifier = Seq2SeqSimplifier.load(source)

    sentences = df_simp["sentence"].tolist()
    split_simples: list[list[str]] = []
    for i in range(0, len(sentences), BATCH_SIZE):
        split_simples.extend(simplifier.simplify(sentences[i : i + BATCH_SIZE]))

    preds_vit5: dict[int, list[dict[str, str]]] = {}
    for (_, row), simples in zip(df_simp.iterrows(), split_simples):
        item_id = int(row["id"])
        preds_vit5[item_id] = extract_triples_from_texts(simples, spo_tagger)

    summary_vit5, rows_vit5 = evaluate_pipeline(
        f"2. {simplifier_key.upper()} + PhoBERT-SPO", preds_vit5, gold_by_id, df_simp
    )
    all_summaries.append(summary_vit5)
    all_pred_rows.extend(rows_vit5)

    # 3. GPT-4.1-mini (LLM zero-shot) + PhoBERT-SPO
    print("\n[3/4] Đang đánh giá Pipeline 3: gpt-4.1-mini Simplifier + PhoBERT-SPO...")
    gpt_simples_by_id = load_gpt_simples(df_simp)
    preds_gpt: dict[int, list[dict[str, str]]] = {}
    for _, row in df_simp.iterrows():
        item_id = int(row["id"])
        preds_gpt[item_id] = extract_triples_from_texts(gpt_simples_by_id[item_id], spo_tagger)

    summary_gpt, rows_gpt = evaluate_pipeline(
        "3. gpt-4.1-mini + PhoBERT-SPO", preds_gpt, gold_by_id, df_simp
    )
    all_summaries.append(summary_gpt)
    all_pred_rows.extend(rows_gpt)

    # 4. Upper-bound: Gold Simples + PhoBERT-SPO
    print("\n[4/4] Đang đánh giá Pipeline 4: Gold Simples + PhoBERT-SPO (Upper-bound)...")
    preds_gold: dict[int, list[dict[str, str]]] = {}
    for _, row in df_simp.iterrows():
        item_id = int(row["id"])
        gold_simples = str(row["simple_sentences"]).split(SENTENCE_SEPARATOR)
        preds_gold[item_id] = extract_triples_from_texts(gold_simples, spo_tagger)

    summary_gold, rows_gold = evaluate_pipeline(
        "4. Gold Simples + PhoBERT-SPO (Upper-bound)", preds_gold, gold_by_id, df_simp
    )
    all_summaries.append(summary_gold)
    all_pred_rows.extend(rows_gold)

    # In kết quả
    print("\n" + "=" * 105)
    print("KẾT QUẢ ĐÁNH GIÁ DOWNSTREAM SPO THEO CÁC PHƯƠNG ÁN TÁCH CÂU (182 CÂU PHỨC TEST)")
    print("=" * 105)
    df_metrics = pd.DataFrame(all_summaries)
    print(df_metrics.to_string(index=False))
    print("=" * 105)

    # Lưu file
    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_metrics.to_csv(METRICS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame(all_pred_rows).to_csv(PREDICTIONS_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[+] Đã lưu metrics tổng hợp tại: {METRICS_OUTPUT_PATH}")
    print(f"[+] Đã lưu dự đoán chi tiết tại: {PREDICTIONS_OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Đánh giá Downstream SPO giữa các phương pháp tách câu.")
    parser.add_argument("--model", choices=sorted(SIMPLIFIER_VARIANTS), default="vit5")
    args = parser.parse_args()
    run_evaluations(args)


if __name__ == "__main__":
    main()
