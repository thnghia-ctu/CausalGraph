import re
from collections import defaultdict

from configs.config import CAUSAL_TRIGGERS_PATH
from src.data_models.dependency_token import Sentence
from src.data_models.trigger import Trigger
from src.utils.helpers import load_xlsx


class TriggerCausalClassifier:
    """Nhãn yếu (weak label) câu nhân quả dựa trên danh sách trigger có sẵn."""

    def __init__(self):
        df = load_xlsx(file_path=CAUSAL_TRIGGERS_PATH)
        self.causal_triggers: dict[str, str] = {
            self._normalize(trigger): polarity
            for trigger, polarity in zip(df["trigger"], df["polarity"])
        }

        self.trigger_index: dict[str, list[str]] = defaultdict(list)
        for norm_trigger in self.causal_triggers.keys():
            word_seq = norm_trigger.split("_")
            self.trigger_index[word_seq[0]].append(norm_trigger)

        for first_word in self.trigger_index:
            self.trigger_index[first_word].sort(key=len, reverse=True)

        raw_triggers = sorted(
            {str(trigger).strip() for trigger in df["trigger"] if str(trigger).strip()},
            key=len,
            reverse=True,
        )
        self._text_patterns = [
            (trigger, self._build_pattern(trigger))
            for trigger in raw_triggers
        ]

    # Từ/cụm đứng trước trigger khiến nó KHÔNG còn mang nghĩa nhân quả
    # (vd. "thay vì" = "instead of", khác hẳn "vì" = "because").
    _EXCLUDE_PRECEDING: dict[str, list[str]] = {
        "vì": ["thay"],
    }

    @classmethod
    def _build_pattern(cls, trigger: str) -> re.Pattern:
        lookbehinds = "".join(
            rf"(?<!\b{re.escape(word)} )"
            for word in cls._EXCLUDE_PRECEDING.get(trigger, [])
        )
        return re.compile(rf"{lookbehinds}\b{re.escape(trigger)}\b", re.IGNORECASE)

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().replace(" ", "_").lower()

    def find_trigger_matches(self, text: str) -> list[str]:
        """So khớp trigger trực tiếp trên câu thô (không cần VnCoreNLP)."""
        return [trigger for trigger, pattern in self._text_patterns if pattern.search(text)]

    def is_causal_text(self, text: str) -> bool:
        return bool(self.find_trigger_matches(text))

    def predict(self, texts: list[str]) -> list[str]:
        return ["causal" if self.find_trigger_matches(text) else "non_causal" for text in texts]

    def find_triggers(self, sentence: Sentence) -> list[Trigger]:
        tokens = sentence.tokens
        n_tokens = len(tokens)
        found: list[Trigger] = []
        used_ids: set[int] = set()

        for i in range(n_tokens):
            if tokens[i].id in used_ids:
                continue

            first_word = self._normalize(tokens[i].word).split("_")[0]
            candidates = self.trigger_index.get(first_word)
            if not candidates:
                continue
            for word_seq in candidates:
                span_len = len(word_seq)
                j = i
                trig = "_".join(self._normalize(tok.word) for tok in tokens[i:j + 1])
                while span_len < len(trig) and j < n_tokens - 1:
                    j += 1
                    trig = "_".join(self._normalize(tok.word) for tok in tokens[i:j + 1])
                if trig == word_seq:
                    found.append(Trigger(
                        start_id=tokens[i].id,
                        end_id=tokens[j].id,
                        text=word_seq,
                    ))
                    used_ids.update(range(tokens[i].id, tokens[j].id + 1))

        return sorted(found, key=lambda tr: tr.start_id)

    def is_causal(self, sentence: Sentence) -> bool:
        return bool(self.find_triggers(sentence))
