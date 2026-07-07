# -*- coding: utf-8 -*-
"""
debug_causal_patterns.py
-------------------------
Mục đích: kiểm chứng TRỰC TIẾP (không suy đoán qua CSV) 3 giả thuyết đã nêu:

  (A) "giúp" khi là ROOT của câu (kiểu "NP + giúp + VP") có complement được
      gắn nhãn dependency là gì? Có phải "vmod" (không nằm trong role-set
      của has_obj trong is_direct_svo) hay không?

  (B) "hỗ_trợ" trong các cụm danh từ ghép kiểu "chính_sách hỗ_trợ",
      "công_cụ hỗ_trợ" có thực sự được VnCoreNLP gán POS = V (nên vượt qua
      bộ lọc `anchor.pos not in {"V","A"}` trong RelationExtractor) hay
      POS = N (và lẽ ra phải bị loại từ sớm)?

  (C) coord_conj: các nhãn dependency "conj" / "coord" có thực sự tồn tại
      trong output của VnCoreNLPParser trên corpus này không, hay bộ gán
      nhãn dùng ký hiệu khác (vd "cc", "conj" viết hoa/thường khác, ...)?

CHẠY FILE NÀY TRỰC TIẾP TRONG MÔI TRƯỜNG DỰ ÁN CỦA BẠN (có Java/VnCoreNLP,
có các module src.*). Tôi không có quyền truy cập VnCoreNLP/dữ liệu gốc nên
không tự chạy được — script này chỉ soạn sẵn để BẠN chạy và xem output.

LƯU Ý VỀ SCHEMA: tôi chưa thấy code của DependencyToken/Sentence/DependencyTree
nên KHÔNG chắc tên field chính xác (vd `head_id` vs `head` vs `parent_id`).
Phần STEP 0 sẽ tự in ra toàn bộ attribute của token bằng vars()/__dict__ để
bạn xác nhận tên field thật, nếu các đoạn sau lỗi AttributeError thì sửa
lại tên field cho khớp.
"""

import sys
import traceback
from collections import Counter, defaultdict

from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.dependency_tree import DependencyTree
from src.extraction.causal_patterns import classify_structure


# =====================================================================
# STEP 0 — Soi schema thật của DependencyToken (chạy 1 lần đầu tiên)
# =====================================================================
def probe_schema(sentence):
    print("\n=== STEP 0: SCHEMA PROBE (token đầu tiên) ===")
    tok = sentence.tokens[0]
    try:
        print("vars(token) =", vars(tok))
    except TypeError:
        print("__dict__ =", tok.__dict__)
    print("Danh sách attribute public:", [a for a in dir(tok) if not a.startswith("_")])
    print("=" * 60)


def dump_sentence_table(sentence):
    """In toàn bộ token: id, word, pos, dep, head (thử nhiều tên field)."""
    print(f"{'id':<4}{'word':<20}{'pos':<8}{'dep':<12}{'head_id/word'}")
    for tok in sentence.tokens:
        head_repr = "?"
        for head_attr in ("head_id", "head", "parent_id", "head_word"):
            if hasattr(tok, head_attr):
                head_repr = getattr(tok, head_attr)
                break
        print(f"{tok.id:<4}{tok.word:<20}{getattr(tok,'pos','?'):<8}{getattr(tok,'dep','?'):<12}{head_repr}")


# =====================================================================
# STEP 1 — Test các câu mẫu cụ thể (đúng nghĩa các câu đã thấy trong CSV,
# nhưng viết lại thành TEXT THÔ - không có dấu "_" nối từ).
#
# QUAN TRỌNG: cột "sentence" trong relations3.csv là OUTPUT đã qua
# word-segmentation của VnCoreNLP (word ghép đã nối bằng "_"). Đưa text
# đã có "_" ngược vào parse_text() sẽ khiến VnCoreNLP segment chồng lần 2,
# lệch số lượng token giữa layer segmentation và layer POS/NER -> chính là
# nguyên nhân ArrayIndexOutOfBoundsException trong NerRecognizer bạn gặp.
# Do đó ở đây dùng câu THÔ (dấu cách bình thường, không có "_").
# =====================================================================

# Câu sanity-check đơn giản để xác nhận pipeline chạy được trước khi thử
# các câu phức tạp hơn.
SANITY_SENTENCE = "Chuyển đổi số giúp nông dân tăng năng suất."

# Nhóm A: nghi vấn "giúp" root + VP-complement bị gắn nhãn vmod
SENTENCES_GROUP_A = [
    "Điều này giúp tăng cường hiệu quả và giảm công sức lao động trong quá trình chăm sóc cây trồng.",
    "Những ứng dụng này giúp giảm một nửa chi phí sản xuất và công sức lao động.",
    "Công nghệ này giúp khai thác các dữ liệu hiện có để dự báo cho các xu hướng trong tương lai.",
    "Điều này sẽ giúp tăng khả năng hiển thị dọc theo chuỗi cung ứng.",
]

# Nhóm B: nghi vấn "hỗ trợ" là định ngữ danh từ (chính sách hỗ trợ, công cụ hỗ trợ)
SENTENCES_GROUP_B = [
    "Nếu không có chính sách hỗ trợ chuyển đổi nghề nghiệp phù hợp, tình trạng thất nghiệp có thể gia tăng.",
    "Chính phủ cũng đã có nhiều chính sách hỗ trợ nhằm thúc đẩy chuyển đổi số trong nông nghiệp.",
    "Đưa dữ liệu trở thành công cụ hỗ trợ ra quyết định trong sản xuất.",
]

# Nhóm C: câu có cấu trúc liệt kê rõ ràng, để kiểm tra coord_conj có bao giờ bắt được không
SENTENCES_GROUP_C = [
    "Chuyển đổi số giúp giảm chi phí, tăng năng suất và mở rộng thị trường tiêu thụ nông sản.",
    "Nông dân, doanh nghiệp và hợp tác xã cùng tham gia thúc đẩy chuyển đổi số.",
]


def run_case(text, relation_extractor, show_schema=False):
    print("\n" + "#" * 70)
    print("CÂU:", text)
    print("#" * 70)

    try:
        sentences = VnCoreNLPParser.parse_text(text)
    except Exception as e:
        print(f">> LỖI khi parse câu này: {e}")
        print(">> Bỏ qua câu này, tiếp tục câu kế tiếp.")
        return

    for sentence in sentences:
        if show_schema:
            probe_schema(sentence)
        dump_sentence_table(sentence)

        triggers = relation_extractor.find_triggers(sentence)
        if not triggers:
            print(">> Không tìm thấy trigger nào trong câu này (kiểm tra lại trigger_index).")
            continue

        tree = DependencyTree(sentence)
        for trigger in triggers:
            print(f"\n--- Trigger: '{trigger.text}' (token id {trigger.start_id}-{trigger.end_id}) ---")
            anchor = tree.find_trigger_head(trigger)
            print(f"anchor.word={anchor.word} | anchor.pos={getattr(anchor,'pos','?')} | anchor.dep={getattr(anchor,'dep','?')}")

            if getattr(anchor, "pos", None) not in {"V", "A"}:
                print(">> anchor.pos KHÔNG thuộc {V,A} -> bị loại ngay ở RelationExtractor (continue), "
                      "không tới bước classify_structure. XÁC NHẬN giả thuyết Nhóm B nếu đây là câu B.")
                continue

            # In TẤT CẢ dependents của anchor (không lọc theo role-set của pattern)
            # để thấy nhãn dep THẬT của complement là gì.
            # LƯU Ý: không dùng tree.find_dependents(anchor) ở đây vì hàm này có thể
            # âm thầm trả về rỗng nếu không truyền roles (đã xác nhận qua log thực tế).
            # Lấy trực tiếp theo field "head" (đã xác nhận đúng tên qua STEP 0 probe).
            all_deps = [t for t in sentence.tokens if getattr(t, "head", None) == anchor.id]

            print("Tất cả dependents của anchor (word / dep / pos):")
            for d in all_deps:
                print(f"   - {d.word:<15} dep={getattr(d,'dep','?'):<10} pos={getattr(d,'pos','?')}")

            pattern = classify_structure(trigger, tree)
            print(f">> KẾT QUẢ classify_structure = '{pattern}'")

            if pattern == "unmatched":
                dep_labels = sorted(set(getattr(d, "dep", "?") for d in all_deps))
                print(f">> GIẢ THUYẾT: nếu trong {dep_labels} có 'vmod' mà is_direct_svo không nhận "
                      f"'vmod' vào role-set của has_obj -> đây chính là gap của Pattern A.")


def step1_manual_cases():
    relation_extractor = RelationExtractor()

    print("\n\n========== SANITY CHECK (xác nhận pipeline chạy được) ==========")
    run_case(SANITY_SENTENCE, relation_extractor, show_schema=True)

    print("\n\n========== NHÓM A: giúp-là-root + VP complement ==========")
    for i, s in enumerate(SENTENCES_GROUP_A):
        run_case(s, relation_extractor, show_schema=(i == 0))

    print("\n\n========== NHÓM B: hỗ_trợ trong cụm danh từ ghép ==========")
    for s in SENTENCES_GROUP_B:
        run_case(s, relation_extractor)

    print("\n\n========== NHÓM C: câu liệt kê, test coord_conj ==========")
    for s in SENTENCES_GROUP_C:
        run_case(s, relation_extractor)


# =====================================================================
# STEP 2 — Quét thống kê trên TOÀN BỘ corpus thật (không chỉ câu mẫu)
#   để trả lời định lượng: "vmod xuất hiện bao nhiêu % trong các case
#   unmatched có anchor.pos hợp lệ?" và "conj/coord có tồn tại trong
#   toàn bộ output VnCoreNLP của bạn không?"
# =====================================================================
def step2_corpus_scan(root_dir, doc_range=range(1, 19)):
    from src.chunking.semantic_chunker import SemanticChunker
    from src.filtering.semantic_filter import filter_chunks
    from src.utils.helpers import load_txt

    relation_extractor = RelationExtractor()
    chunker = SemanticChunker()

    all_dep_labels = Counter()                 # toàn bộ nhãn dep xuất hiện trong corpus
    unmatched_complement_roles = Counter()      # nhãn dep của complement khi pattern=unmatched
    trigger_pattern_count = defaultdict(Counter)  # trigger -> {pattern: count}
    trigger_is_first_conjunct = 0                # đếm trigger có con mang dep=="coord" (nghi vấn coord_conj một chiều)
    trigger_is_later_conjunct = 0                # đếm trigger có dep=="conj" hoặc cha có dep=="coord"

    for i in doc_range:
        path = f"{root_dir}/data/raw/web/{i}_text.txt"
        try:
            text = load_txt(path)
            if not text:
                continue
            chunks = [c.text for c in chunker.chunk(text)]
            filtered_chunks, _ = filter_chunks(chunks)
            filter_text = " ".join(filtered_chunks)
        except Exception as e:
            print(f"[doc {i}] lỗi đọc/chunk: {e}")
            continue

        try:
            sentences = VnCoreNLPParser.parse_text(filter_text)
        except Exception as e:
            print(f"[doc {i}] lỗi parse VnCoreNLP: {e}")
            continue

        for sentence in sentences:
            for tok in sentence.tokens:
                all_dep_labels[getattr(tok, "dep", "?")] += 1

            triggers = relation_extractor.find_triggers(sentence)
            if not triggers:
                continue
            tree = DependencyTree(sentence)
            for trigger in triggers:
                anchor = tree.find_trigger_head(trigger)
                if getattr(anchor, "pos", None) not in {"V", "A"}:
                    continue
                pattern = classify_structure(trigger, tree)
                trigger_pattern_count[trigger.text][pattern] += 1

                # Kiểm chứng giả thuyết coord_conj một chiều:
                anchor_children = [t for t in sentence.tokens if getattr(t, "head", None) == anchor.id]
                if any(getattr(c, "dep", None) == "coord" for c in anchor_children):
                    trigger_is_first_conjunct += 1
                anchor_head = tree.find_parent(anchor) if hasattr(tree, "find_parent") else None
                if getattr(anchor, "dep", None) == "conj" or (anchor_head is not None and getattr(anchor_head, "dep", None) == "coord"):
                    trigger_is_later_conjunct += 1

                if pattern == "unmatched":
                    deps = [t for t in sentence.tokens if getattr(t, "head", None) == anchor.id]
                    for d in deps:
                        if getattr(d, "pos", None) in {"V", "A"}:
                            unmatched_complement_roles[getattr(d, "dep", "?")] += 1

    print("\n\n========== KẾT QUẢ QUÉT TOÀN CORPUS ==========")

    print("\n-- Tần suất TẤT CẢ nhãn dependency xuất hiện trong corpus --")
    for label, cnt in all_dep_labels.most_common(30):
        flag = "  <-- coord_conj cần nhãn này" if label in ("conj", "coord") else ""
        print(f"{label:<15}{cnt}{flag}")
    if not any(l in all_dep_labels for l in ("conj", "coord")):
        print(">> XÁC NHẬN: nhãn 'conj'/'coord' KHÔNG hề xuất hiện trong toàn bộ corpus "
              "-> coord_conj chắc chắn không thể match, do sai tên nhãn trong is_coord_conj/handle_coord_conj. "
              "Cần xem bảng nhãn dependency thật mà VnCoreNLPParser trả về và sửa lại chuỗi so_sánh.")

    print("\n-- Nhãn dep của complement (V/A) khi anchor hợp lệ nhưng pattern=unmatched --")
    for label, cnt in unmatched_complement_roles.most_common(20):
        flag = "  <-- NGHI VẤN: nếu đây là 'vmod', bổ_sung vào role-set has_obj sẽ vá được nhóm này" if label == "vmod" else ""
        print(f"{label:<15}{cnt}{flag}")

    print("\n-- Kiểm chứng giả thuyết coord_conj một chiều --")
    print(f"Số lần trigger là ITEM ĐẦU chuỗi liệt kê (có con dep=='coord'): {trigger_is_first_conjunct}")
    print(f"Số lần trigger là ITEM SAU chuỗi liệt kê (dep=='conj' hoặc cha dep=='coord'): {trigger_is_later_conjunct}")
    if trigger_is_first_conjunct > 0 and trigger_is_later_conjunct == 0:
        print(">> XÁC NHẬN MẠNH giả thuyết: toàn bộ trigger nằm trong coordination đều ở vị trí ĐẦU chuỗi, "
              "đúng như is_coord_conj chỉ xử lý chiều 'trigger ở sau' -> giải thích trọn vẹn vì sao coord_conj=0.")

    print("\n-- Tỷ lệ match theo từng trigger (top 15 trigger tần suất cao nhất) --")
    trigger_totals = {t: sum(c.values()) for t, c in trigger_pattern_count.items()}
    for trig, total in sorted(trigger_totals.items(), key=lambda x: -x[1])[:15]:
        counts = trigger_pattern_count[trig]
        unmatched_pct = counts.get("unmatched", 0) / total * 100
        print(f"{trig:<15} total={total:<5} unmatched={counts.get('unmatched',0):<5} ({unmatched_pct:.1f}%)  detail={dict(counts)}")

    return all_dep_labels, unmatched_complement_roles, trigger_pattern_count


if __name__ == "__main__":
    print("Chạy STEP 1 (test case cụ thể, đọc kỹ output để xác nhận từng giả thuyết)...")
    try:
        step1_manual_cases()
    except Exception:
        print("STEP 1 lỗi -- có thể do tên field/method không khớp schema thật. Traceback:")
        traceback.print_exc()

    # Bỏ comment dòng dưới để chạy quét toàn corpus (STEP 2) sau khi STEP 1 đã chạy ổn
    # ROOT_DIR = "D:\\CausalGraph"
    # step2_corpus_scan(ROOT_DIR)