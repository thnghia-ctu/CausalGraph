import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configs.config import BASE_DIR

FIELDNAMES = [
    "id",
    "group",
    "sentence",
    "expected_label",
    "expected_has_explicit_trigger",
    "expected_trigger_text",
    "note",
]

CASES = [
    ("trigger_but_vague_ab", "Nhiều nguyên nhân dẫn đến việc nông dân chậm chuyển đổi số.",
     "non_causal", False, "",
     "A ('nhiều nguyên nhân') là cụm lượng hóa mơ hồ, không chỉ đích danh nguyên nhân nào."),
    ("trigger_but_vague_ab", "Do thiếu hạ tầng internet, nhiều xã vùng sâu chưa thể triển khai nông nghiệp thông minh.",
     "causal", True, "do",
     "A và B đều cụ thể: thiếu hạ tầng internet -> chưa thể triển khai nông nghiệp thông minh."),
    ("trigger_but_vague_ab", "Việc chậm chuyển đổi số bắt nguồn từ nhiều lý do khác nhau.",
     "non_causal", False, "",
     "B ('nhiều lý do khác nhau') mơ hồ dù động từ 'bắt nguồn từ' mang nghĩa nhân quả."),

    ("purpose_de_nham", "Hợp tác xã lắp đặt hệ thống giám sát để giảm thất thoát nước tưới.",
     "causal", True, "để",
     "Mệnh đề mục đích nêu trạng thái cụ thể bị tác động (giảm thất thoát nước)."),
    ("purpose_de_nham", "Doanh nghiệp tổ chức tập huấn nhằm nâng cao kỹ năng số cho nông dân.",
     "causal", True, "nhằm",
     "Mệnh đề mục đích nêu trạng thái cụ thể (nâng cao kỹ năng số)."),
    ("purpose_de_nham", "Nông dân ra thành phố để gặp gỡ đối tác thu mua.",
     "non_causal", False, "",
     "Mệnh đề mục đích chỉ là hành động tiếp theo, không phải trạng thái bị tác động."),

    ("weak_causal_verbs", "Thu nhập hộ gia đình ảnh hưởng đến quyết định đầu tư máy móc nông nghiệp.",
     "causal", True, "ảnh hưởng đến",
     "A, B cụ thể: thu nhập hộ gia đình -> quyết định đầu tư máy móc."),
    ("weak_causal_verbs", "Chuyển đổi số liên quan mật thiết đến phát triển nông thôn.",
     "non_causal", False, "",
     "'liên quan' biểu thị tương quan, không xác định chiều tác động."),
    ("weak_causal_verbs", "Trình độ học vấn của chủ hộ tác động đến tốc độ tiếp nhận công nghệ mới.",
     "causal", True, "tác động đến",
     "A, B cụ thể và có chiều tác động rõ."),

    ("implicit_vs_temporal", "Mất mùa liên tiếp, nhiều hộ nông dân buộc phải vay vốn ngân hàng.",
     "causal", False, "",
     "Không có từ nối nhưng thứ tự lý do -> hệ quả là bắt buộc."),
    ("implicit_vs_temporal", "Vụ mùa kết thúc, nông dân bắt đầu chuẩn bị cho vụ tiếp theo.",
     "non_causal", False, "",
     "Trình tự thời gian thuần túy, không có tín hiệu tác động."),
    ("implicit_vs_temporal", "Giá cà phê rớt mạnh, nhiều nông hộ chuyển sang trồng cây ăn trái.",
     "causal", False, "",
     "Ca biên cố ý đưa vào để theo dõi độ nhất quán: test 'vì vậy' chèn tự nhiên hơn 'và', theo hướng dẫn hiện tại nghiêng về causal."),
    ("implicit_vs_temporal", "Chi phí sản xuất tăng, nhiều hộ giảm diện tích canh tác.",
     "non_causal", False, "",
     "Test 'vì vậy' và 'và' đều chèn tự nhiên như nhau -> lưỡng lự -> non_causal (case đối chiếu, đã có trong prompt)."),

    ("hedging", "Nhiều khả năng do chi phí đầu tư ban đầu cao nên nông dân e ngại chuyển đổi số.",
     "causal", True, "nên",
     "Hedging khẳng định vẫn tính causal."),
    ("hedging", "Chưa rõ liệu chi phí đầu tư có phải là rào cản chính khiến nông dân e ngại chuyển đổi số hay không.",
     "non_causal", False, "",
     "Hedging trung lập, không khẳng định quan hệ."),
    ("hedging", "Giá vật tư nông nghiệp có thể không phải là nguyên nhân chính khiến nông dân giảm đầu tư.",
     "non_causal", False, "",
     "Hedging phủ định, không khẳng định tác động."),

    ("negation", "Chi phí đầu tư ban đầu không phải là rào cản khiến nông dân từ chối ứng dụng công nghệ số.",
     "non_causal", False, "",
     "Phủ định thuần túy, không tái khẳng định nguyên nhân khác."),
    ("negation", "Không phải do thiếu vốn mà do thiếu kỹ năng sử dụng công nghệ khiến nông dân chậm chuyển đổi số.",
     "causal", True, "khiến",
     "Phủ định X nhưng tái khẳng định quan hệ khác (thiếu kỹ năng -> chậm chuyển đổi số); đánh giá theo quan hệ được tái khẳng định."),
    ("negation", "Thiếu vốn không phải là nguyên nhân khiến nông dân từ bỏ mô hình canh tác hữu cơ.",
     "non_causal", False, "",
     "Phủ định quan hệ nhân quả, không tái khẳng định nguyên nhân thay thế."),

    ("multi_relation", "Giá vật tư nông nghiệp tăng khiến chi phí sản xuất tăng, nhưng nông dân vẫn duy trì diện tích canh tác để đảm bảo thu nhập.",
     "causal", True, "khiến",
     "Chỉ cần 1 quan hệ hợp lệ (giá vật tư tăng -> chi phí sản xuất tăng) là đủ."),
    ("multi_relation", "Nhờ chính sách hỗ trợ lãi suất, nhiều hộ dân đã mạnh dạn vay vốn đầu tư máy móc, đồng thời tham gia các lớp tập huấn kỹ thuật.",
     "causal", True, "nhờ",
     "Quan hệ chính sách hỗ trợ lãi suất -> mạnh dạn vay vốn đầu tư là đủ để gán causal."),
    ("multi_relation", "Nông dân vừa ứng dụng cảm biến đất vừa áp dụng tưới nhỏ giọt, đồng thời ghi chép nhật ký canh tác điện tử.",
     "non_causal", False, "",
     "Chỉ liệt kê các hành động song song, không có quan hệ A -> B nào."),

    ("event_state_ab", "Việc thiếu nhân lực có chuyên môn về công nghệ khiến nhiều hợp tác xã chậm triển khai chuyển đổi số.",
     "causal", True, "khiến",
     "A là cụm danh từ hóa sự việc, vẫn hợp lệ làm A."),
    ("event_state_ab", "Không được tiếp cận vốn vay ưu đãi khiến nhiều hộ nhỏ lẻ khó đầu tư công nghệ mới.",
     "causal", True, "khiến",
     "A là cụm trạng thái phủ định cụ thể, vẫn hợp lệ làm A."),

    ("pronoun_antecedent", "Chuyển đổi số giúp nông dân tiết kiệm thời gian ghi chép sổ sách; điều này khiến họ có thêm thời gian chăm sóc cây trồng.",
     "causal", True, "khiến",
     "'điều này' có tiền ngữ rõ trong cùng câu (việc tiết kiệm thời gian ghi chép sổ sách)."),
    ("pronoun_antecedent", "Điều này khiến nhiều nông dân e ngại.",
     "non_causal", False, "",
     "'điều này' không có tiền ngữ trong chính câu này."),

    ("subordinate_clause", "Nông dân, vì thiếu thông tin thị trường, thường bán nông sản với giá thấp hơn giá trị thực.",
     "causal", True, "vì",
     "Quan hệ nhân quả nằm trong mệnh đề chen giữa, vẫn xác định được A, B cụ thể."),
    ("subordinate_clause", "Các chuyên gia, những người đã nghiên cứu thị trường nông sản nhiều năm, khuyến nghị nông dân nên đa dạng hóa kênh bán hàng.",
     "non_causal", False, "",
     "Mệnh đề phụ chỉ bổ sung thông tin về chuyên gia, không chứa quan hệ nhân quả."),
]


def build_rows() -> list[dict]:
    rows = []
    counters: dict[str, int] = {}
    for group, sentence, label, has_trigger, trigger_text, note in CASES:
        counters[group] = counters.get(group, 0) + 1
        rows.append({
            "id": f"{group}_{counters[group]:02d}",
            "group": group,
            "sentence": sentence,
            "expected_label": label,
            "expected_has_explicit_trigger": has_trigger,
            "expected_trigger_text": trigger_text,
            "note": note,
        })
    return rows


def main():
    output_path = BASE_DIR / "data" / "eval" / "causal_hard_cases.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = build_rows()
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Total {len(rows)} hard cases -> {output_path}")


if __name__ == "__main__":
    main()
