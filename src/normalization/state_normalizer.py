import re
from dataclasses import dataclass

from configs.config import BASE_DIR
from src.utils.helpers import load_xlsx


@dataclass(frozen=True)
class StateMatch:
    """Kết quả nhận diện một biểu đạt trạng thái trong factor mention.

    ``start`` và ``end`` là vị trí ký tự theo khoảng nửa mở ``[start, end)``
    trong chuỗi đã được chuẩn hóa bề mặt. FactorParser có thể dùng khoảng này
    để xác định factor core mà không phải tìm lại biểu đạt trạng thái.
    """

    expression: str
    state: str
    start: int
    end: int


class StateNormalizer:
    """Nhận diện state bằng lexicon trên factor mention đã chuẩn hóa.

    Mỗi biểu đạt được so khớp theo biên từ. Nếu có nhiều kết quả, biểu đạt
    xuất hiện sớm nhất được chọn; tại cùng một vị trí, biểu đạt dài hơn được
    ưu tiên. Vì một ``StateMatch`` chỉ biểu diễn một state, factor phối hợp
    như ``giảm chi phí và tăng năng suất`` cần được tách thành các factor
    nguyên tử trước khi gọi phương thức này.
    """

    def __init__(self) -> None:
        df = load_xlsx(
            file_path=f"{BASE_DIR}/configs/state_lexicon.xlsx",
            sheet_name="state_expressions",
        )
        self.state_lexicon: dict[str, tuple[str, ...]] = (
            df.groupby("state_code", sort=False)["expression"]
            .apply(tuple)
            .to_dict()
        )
        self._patterns = self._compile_patterns(self.state_lexicon)

    @staticmethod
    def _compile_patterns(
        lexicon: dict[str, tuple[str, ...]],
    ) -> list[tuple[str, str, re.Pattern[str]]]:
        patterns = []
        for state, expressions in lexicon.items():
            for raw_expression in expressions:
                expression = " ".join(
                    raw_expression.replace("_", " ").casefold().split()
                )
                if not expression:
                    raise ValueError(
                        f"State expression for {state!r} must not be empty"
                    )

                pattern = re.compile(
                    rf"(?<!\w){re.escape(expression)}(?!\w)"
                )
                patterns.append((expression, state, pattern))
        return patterns

    @staticmethod
    def _is_negated(text: str, start: int, expression: str) -> bool:
        """Kiểm tra phủ định nằm ngay trước một state expression.

        Các expression tự mang nghĩa thiếu vắng như ``không đủ`` và
        ``chưa có`` là state hợp lệ, không bị xem là phủ định của state.
        """
        if expression.startswith(("không ", "chưa ")):
            return False

        prefix = text[:start]
        return re.search(
            r"(?:^|\s)(?:không|chưa)(?:\s+\w+)?\s*$",
            prefix,
        ) is not None

    def normalize(self, text: str) -> StateMatch | None:
        """Tìm biểu đạt trạng thái và ánh xạ nó về state chuẩn.

        Args:
            text: Factor mention đã được chuẩn hóa bề mặt.

        Returns:
            Thông tin state được nhận diện, hoặc ``None`` nếu factor không
            chứa biểu đạt trạng thái đã biết.
        """
        matches: list[StateMatch] = []
        for expression, state, pattern in self._patterns:
            for result in pattern.finditer(text):
                if self._is_negated(text, result.start(), expression):
                    continue
                matches.append(
                    StateMatch(
                        expression=result.group(),
                        state=state,
                        start=result.start(),
                        end=result.end(),
                    )
                )

        if not matches:
            return None

        return min(
            matches,
            key=lambda match: (match.start, -(match.end - match.start)),
        )
