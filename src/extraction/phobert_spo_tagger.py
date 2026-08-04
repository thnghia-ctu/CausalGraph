import unicodedata
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)
from transformers.trainer_utils import get_last_checkpoint
from underthesea import word_tokenize

from configs.config import SPO_TAGGER_MODEL_DIR
from src.data_models.factor import Factor
from src.data_models.svo_triple import SVOTriple

DEFAULT_MODEL_NAME = "vinai/phobert-base"
MAX_LENGTH = 256

BIO_LABELS = ["O", "B-SUBJ", "I-SUBJ", "B-PRED", "I-PRED", "B-OBJ", "I-OBJ"]
_LABEL2ID = {label: i for i, label in enumerate(BIO_LABELS)}
_ID2LABEL = {i: label for label, i in _LABEL2ID.items()}


def _words_and_offsets(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Tách từ bằng underthesea; trả về danh sách từ (âm tiết ghép bằng "_" cho đúng
    định dạng PhoBERT) cùng khoảng ký tự (start, end) của từng từ trong `text` gốc,
    dùng để quy chiếu ngược span subject/predicate/object về chỉ số từ mà không cần
    tách từ riêng cho từng span (dễ lệch do underthesea phân đoạn phụ thuộc ngữ cảnh).

    So khớp qua bản bỏ khoảng trắng + bỏ dấu thanh thay vì `text.find(token)` trực
    tiếp, vì underthesea có thể trả về token với cách gõ dấu khác câu gốc (vd. token
    "hóa" cho câu gốc viết "hoá") — so khớp nguyên văn sẽ thất bại và âm thầm làm mất
    từ đó, kéo lệch toàn bộ offset phía sau."""
    fold_text, positions = _compact(text, _strip_tone_char)

    words, offsets, cursor = [], [], 0
    for token in word_tokenize(text):
        fold_token, _ = _compact(token, _strip_tone_char)
        if not fold_token:
            continue
        idx = fold_text.find(fold_token, cursor)
        if idx == -1:
            idx = fold_text.find(fold_token)
        if idx == -1:
            continue
        words.append(token.replace(" ", "_"))
        offsets.append((positions[idx], positions[idx + len(fold_token) - 1] + 1))
        cursor = idx + len(fold_token)
    return words, offsets


_TONE_MARKS = {"́", "̀", "̉", "̃", "̣"}  # sắc, huyền, hỏi, ngã, nặng


def _strip_tone_char(ch: str) -> str:
    """Bỏ dấu thanh của một ký tự, giữ nguyên các dấu khác (â, ê, ô, ơ, ư, đ...).
    NFD phân rã theo từng ký tự đơn giữ đúng 1-1 vị trí (không tạo cụm nhiều ký tự)."""
    decomposed = unicodedata.normalize("NFD", ch)
    stripped = "".join(c for c in decomposed if c not in _TONE_MARKS)
    return unicodedata.normalize("NFC", stripped) or ch


def _compact(text: str, fold=lambda ch: ch) -> tuple[str, list[int]]:
    """Bỏ khoảng trắng, áp `fold` lên từng ký tự còn lại, giữ ánh xạ về vị trí ký tự gốc."""
    chars, positions = [], []
    for i, ch in enumerate(text):
        if ch.isspace():
            continue
        chars.append(fold(ch))
        positions.append(i)
    return "".join(chars), positions


_FOLDS = (
    lambda ch: ch,
    lambda ch: ch.casefold(),
    _strip_tone_char,
    lambda ch: _strip_tone_char(ch).casefold(),
)


def _find_char_span(text: str, span_text: str) -> tuple[int, int] | None:
    """So khớp span_text trong text, nới lỏng dần qua từng bước: nguyên văn, bỏ khoảng
    trắng (CSV ghép span từ token đã tách nên spacing quanh dấu câu có thể lệch, vd
    "sửa chữa , cải tạo" so với "sửa chữa, cải tạo"), không phân biệt hoa/thường (một số
    nguồn dữ liệu viết thường chữ đầu span dù câu gốc viết hoa), và bỏ dấu thanh (VnCoreNLP/
    underthesea có thể chuẩn hoá lại cách gõ dấu, vd "số hóa" so với "số hoá")."""
    span_text = span_text.strip()
    if not span_text:
        return None

    start = text.find(span_text)
    if start != -1:
        return start, start + len(span_text)

    for fold in _FOLDS:
        compact_text, positions = _compact(text, fold)
        compact_span, _ = _compact(span_text, fold)
        if not compact_span:
            continue
        idx = compact_text.find(compact_span)
        if idx != -1:
            return positions[idx], positions[idx + len(compact_span) - 1] + 1

    return None


def _build_labels(
    sentence: str, subject: str, predicate: str, object_: str
) -> tuple[list[str], list[str]] | None:
    """Tách từ câu và gán nhãn BIO dựa trên vị trí ký tự của subject/predicate/object
    trong câu gốc. Trả về None nếu một span không định vị được (text gán nhãn không phải
    chuỗi con của câu). Câu không có quan hệ (cả ba cột đều rỗng) là mẫu âm hợp lệ theo
    2.4.2, giữ lại với nhãn toàn "O" thay vì bị loại bỏ."""
    words, offsets = _words_and_offsets(sentence)
    labels = ["O"] * len(words)

    if not predicate.strip() and not subject.strip() and not object_.strip():
        return words, labels

    def mark(span_text: str, tag: str) -> bool:
        span = _find_char_span(sentence, span_text)
        if span is None:
            return False
        start, end = span
        indexes = [i for i, (s, e) in enumerate(offsets) if s < end and e > start]
        if not indexes:
            return False
        labels[indexes[0]] = f"B-{tag}"
        for idx in indexes[1:]:
            labels[idx] = f"I-{tag}"
        return True

    if not predicate or not mark(predicate, "PRED"):
        return None
    if subject and not mark(subject, "SUBJ"):
        return None
    if object_ and not mark(object_, "OBJ"):
        return None

    return words, labels


class PhoBertSpoTagger:
    """Trích bộ ba subject-predicate-object bằng PhoBERT + BIO token classification.

    Huấn luyện trực tiếp trên text thô (sentence, subject, predicate, object dạng
    chuỗi con của sentence) lấy thẳng từ CSV, không cần VnCoreNLP.

    PhoBERT dùng tokenizer chậm (không phải fast, không có `.word_ids()`) và chỉ nhận
    văn bản đã tách từ, nên việc căn subword <-> word phải làm thủ công qua
    `_encode_words` thay vì `is_split_into_words=True`.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=len(BIO_LABELS),
            id2label=_ID2LABEL,
            label2id=_LABEL2ID,
        )

    def _encode_words(self, words: list[str]) -> tuple[list[int], list[int]]:
        """Trả về input_ids và word_index (chỉ số word nguồn của từng subword,
        -1 cho token đặc biệt), giới hạn ở MAX_LENGTH."""
        input_ids = [self.tokenizer.bos_token_id]
        word_index = [-1]
        for i, word in enumerate(words):
            pieces = self.tokenizer.tokenize(word) or [self.tokenizer.unk_token]
            input_ids.extend(self.tokenizer.convert_tokens_to_ids(pieces))
            word_index.extend([i] * len(pieces))
        input_ids.append(self.tokenizer.eos_token_id)
        word_index.append(-1)
        return input_ids[:MAX_LENGTH], word_index[:MAX_LENGTH]

    def _tokenize_and_align(self, examples: dict) -> dict:
        all_input_ids, all_labels = [], []
        for words, labels in zip(examples["words"], examples["labels"]):
            input_ids, word_index = self._encode_words(words)
            label_ids, seen = [], set()
            for idx in word_index:
                if idx == -1:
                    label_ids.append(-100)
                elif idx not in seen:
                    label_ids.append(_LABEL2ID[labels[idx]])
                    seen.add(idx)
                else:
                    tag = labels[idx]
                    label_ids.append(_LABEL2ID[f"I-{tag[2:]}"] if tag != "O" else _LABEL2ID["O"])
            all_input_ids.append(input_ids)
            all_labels.append(label_ids)

        return {
            "input_ids": all_input_ids,
            "attention_mask": [[1] * len(ids) for ids in all_input_ids],
            "labels": all_labels,
        }

    def _to_dataset(self, examples: list[tuple[str, str, str, str]]) -> Dataset:
        words_list, labels_list = [], []
        for sentence, subject, predicate, object_ in examples:
            result = _build_labels(sentence, subject, predicate, object_)
            if result is None:
                continue
            words, labels = result
            words_list.append(words)
            labels_list.append(labels)

        print(f"Aligned {len(words_list)}/{len(examples)} examples")
        dataset = Dataset.from_dict({"words": words_list, "labels": labels_list})
        return dataset.map(self._tokenize_and_align, batched=True, remove_columns=["words", "labels"])

    def fit(
        self,
        train_examples: list[tuple[str, str, str, str]],
        eval_examples: list[tuple[str, str, str, str]] | None = None,
        output_dir: str | Path = SPO_TAGGER_MODEL_DIR,
        num_train_epochs: int = 20,
        per_device_train_batch_size: int = 16,
        early_stopping_patience: int = 3,
        resume: bool = True,
    ) -> Trainer:
        """Mỗi example là (sentence, subject, predicate, object) dạng text thô — subject/
        predicate/object phải xuất hiện nguyên văn trong sentence. num_train_epochs là
        mức trần; nếu có eval_examples, training tự dừng sớm khi eval_loss không cải
        thiện sau `early_stopping_patience` lần eval liên tiếp."""
        train_dataset = self._to_dataset(train_examples)
        eval_dataset = self._to_dataset(eval_examples) if eval_examples else None

        collator = DataCollatorForTokenClassification(self.tokenizer)

        args = TrainingArguments(
            output_dir=str(output_dir),
            per_device_train_batch_size=per_device_train_batch_size,
            per_device_eval_batch_size=per_device_train_batch_size,
            num_train_epochs=num_train_epochs,
            save_strategy="steps",
            save_steps=50,
            save_total_limit=2,
            logging_steps=10,
            eval_strategy="steps" if eval_dataset is not None else "no",
            eval_steps=50,
            load_best_model_at_end=eval_dataset is not None,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            fp16=torch.cuda.is_available(),
            report_to="none",
        )

        callbacks = (
            [EarlyStoppingCallback(early_stopping_patience=early_stopping_patience)]
            if eval_dataset is not None else []
        )

        trainer = Trainer(
            model=self.model,
            args=args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=collator,
            processing_class=self.tokenizer,
            callbacks=callbacks,
        )

        checkpoint = get_last_checkpoint(output_dir) if resume and Path(output_dir).exists() else None
        trainer.train(resume_from_checkpoint=checkpoint)
        return trainer

    def extract(self, text: str) -> SVOTriple | None:
        words, _ = _words_and_offsets(text)
        if not words:
            return None

        input_ids, word_index = self._encode_words(words)
        inputs = {
            "input_ids": torch.tensor([input_ids]),
            "attention_mask": torch.tensor([[1] * len(input_ids)]),
        }
        with torch.no_grad():
            logits = self.model(**inputs).logits[0]
        pred_ids = logits.argmax(dim=-1).tolist()

        word_labels: list[str | None] = [None] * len(words)
        for pos, idx in enumerate(word_index):
            if idx != -1 and word_labels[idx] is None:
                word_labels[idx] = _ID2LABEL[pred_ids[pos]]

        return self._decode(words, word_labels)

    @staticmethod
    def _decode(words: list[str], word_labels: list[str | None]) -> SVOTriple | None:
        spans: dict[str, list[int]] = {"SUBJ": [], "PRED": [], "OBJ": []}
        for i, label in enumerate(word_labels):
            if label and label != "O":
                spans[label[2:]].append(i)

        if not spans["PRED"]:
            return None

        def to_factor(tag: str) -> Factor | None:
            ids = spans[tag]
            return Factor(text=" ".join(words[i] for i in ids), token_ids=ids) if ids else None

        predicate_text = " ".join(words[i] for i in spans["PRED"])

        return SVOTriple(subject=to_factor("SUBJ"), predicate=predicate_text, object=to_factor("OBJ"))

    def save(self, path: str | Path = SPO_TAGGER_MODEL_DIR) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)
        self.tokenizer.save_pretrained(path)
        self.model.save_pretrained(path)

    def push_to_hub(self, repo_id: str) -> None:
        self.tokenizer.push_to_hub(repo_id)
        self.model.push_to_hub(repo_id)

    @classmethod
    def load(cls, path: str | Path = SPO_TAGGER_MODEL_DIR) -> "PhoBertSpoTagger":
        instance = cls.__new__(cls)
        instance.model_name = str(path)
        instance.tokenizer = AutoTokenizer.from_pretrained(path)
        instance.model = AutoModelForTokenClassification.from_pretrained(path)
        return instance
