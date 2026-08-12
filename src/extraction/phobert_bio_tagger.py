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

DEFAULT_MODEL_NAME = "vinai/phobert-base"
MAX_LENGTH = 256

_TONE_MARKS = {"́", "̀", "̉", "̃", "̣"}  # sắc, huyền, hỏi, ngã, nặng


def strip_tone_char(ch: str) -> str:
    """Bỏ dấu thanh của một ký tự, giữ nguyên các dấu khác (â, ê, ô, ơ, ư, đ...).
    NFD phân rã theo từng ký tự đơn giữ đúng 1-1 vị trí (không tạo cụm nhiều ký tự)."""
    decomposed = unicodedata.normalize("NFD", ch)
    stripped = "".join(c for c in decomposed if c not in _TONE_MARKS)
    return unicodedata.normalize("NFC", stripped) or ch


def compact(text: str, fold=lambda ch: ch) -> tuple[str, list[int]]:
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
    strip_tone_char,
    lambda ch: strip_tone_char(ch).casefold(),
)


def find_char_span(text: str, span_text: str) -> tuple[int, int] | None:
    """So khớp span_text trong text, nới lỏng dần qua từng bước: nguyên văn, bỏ khoảng
    trắng (một số nguồn dữ liệu ghép span từ token đã tách nên spacing quanh dấu câu có
    thể lệch, vd "sửa chữa , cải tạo" so với "sửa chữa, cải tạo"), không phân biệt hoa/
    thường (một số nguồn viết thường chữ đầu span dù văn bản gốc viết hoa), và bỏ dấu
    thanh (VnCoreNLP/underthesea có thể chuẩn hoá lại cách gõ dấu, vd "số hóa" so với
    "số hoá")."""
    span_text = span_text.strip()
    if not span_text:
        return None

    start = text.find(span_text)
    if start != -1:
        return start, start + len(span_text)

    for fold in _FOLDS:
        compact_text, positions = compact(text, fold)
        compact_span, _ = compact(span_text, fold)
        if not compact_span:
            continue
        idx = compact_text.find(compact_span)
        if idx != -1:
            return positions[idx], positions[idx + len(compact_span) - 1] + 1

    return None


def words_and_offsets(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Tách từ bằng underthesea; trả về danh sách từ (âm tiết ghép bằng "_" cho đúng
    định dạng PhoBERT) cùng khoảng ký tự (start, end) của từng từ trong `text` gốc,
    dùng để quy chiếu ngược span về chỉ số từ mà không cần tách từ riêng cho từng span
    (dễ lệch do underthesea phân đoạn phụ thuộc ngữ cảnh).

    So khớp qua bản bỏ khoảng trắng + bỏ dấu thanh thay vì `text.find(token)` trực
    tiếp, vì underthesea có thể trả về token với cách gõ dấu khác văn bản gốc (vd. token
    "hóa" cho văn bản gốc viết "hoá") — so khớp nguyên văn sẽ thất bại và âm thầm làm
    mất từ đó, kéo lệch toàn bộ offset phía sau."""
    fold_text, positions = compact(text, strip_tone_char)

    words, offsets, cursor = [], [], 0
    for token in word_tokenize(text):
        fold_token, _ = compact(token, strip_tone_char)
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


def mark_span(
    labels: list[str], offsets: list[tuple[int, int]], text: str, span_text: str, tag: str
) -> bool:
    """Định vị span_text trong text rồi gán B-{tag}/I-{tag} vào các word có offset giao
    với span đó. Sửa `labels` tại chỗ, trả về False nếu không định vị được."""
    span = find_char_span(text, span_text)
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


class PhoBertBioTagger:
    """Base BIO token classification bằng PhoBERT, train trực tiếp trên text thô (không
    cần VnCoreNLP). Subclass khai `BIO_LABELS`, `MODEL_DIR` (default path save/load/output)
    và cài `_build_labels`/`_decode` theo bài toán cụ thể.

    PhoBERT dùng tokenizer chậm (không phải fast, không có `.word_ids()`) và chỉ nhận
    văn bản đã tách từ, nên việc căn subword <-> word phải làm thủ công qua
    `_encode_words` thay vì `is_split_into_words=True`.
    """

    BIO_LABELS: list[str] = ["O"]
    MODEL_DIR: Path

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._label2id = {label: i for i, label in enumerate(self.BIO_LABELS)}
        self._id2label = {i: label for label, i in self._label2id.items()}
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=len(self.BIO_LABELS),
            id2label=self._id2label,
            label2id=self._label2id,
        )

    def _build_labels(self, *fields: str) -> tuple[list[str], list[str]] | None:
        raise NotImplementedError

    def _decode(self, words: list[str], word_labels: list[str | None]):
        raise NotImplementedError

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
                    label_ids.append(self._label2id[labels[idx]])
                    seen.add(idx)
                else:
                    tag = labels[idx]
                    label_ids.append(self._label2id[f"I-{tag[2:]}"] if tag != "O" else self._label2id["O"])
            all_input_ids.append(input_ids)
            all_labels.append(label_ids)

        return {
            "input_ids": all_input_ids,
            "attention_mask": [[1] * len(ids) for ids in all_input_ids],
            "labels": all_labels,
        }

    def _to_dataset(self, examples: list[tuple[str, ...]]) -> Dataset:
        words_list, labels_list = [], []
        for fields in examples:
            result = self._build_labels(*fields)
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
        train_examples: list[tuple[str, ...]],
        eval_examples: list[tuple[str, ...]] | None = None,
        output_dir: str | Path | None = None,
        num_train_epochs: int = 100,
        per_device_train_batch_size: int = 16,
        early_stopping_patience: int = 10,
        resume: bool = True,
    ) -> Trainer:
        """Mỗi example là tuple text thô (xem `_build_labels` của subclass để biết thứ tự
        field) — các span phải xuất hiện nguyên văn trong field đầu tiên. num_train_epochs
        là mức trần; nếu có eval_examples, training tự dừng sớm khi eval_loss không cải
        thiện sau `early_stopping_patience` epoch liên tiếp (eval theo epoch, không theo
        step — không phụ thuộc kích thước dataset)."""
        output_dir = output_dir or self.MODEL_DIR
        train_dataset = self._to_dataset(train_examples)
        eval_dataset = self._to_dataset(eval_examples) if eval_examples else None

        collator = DataCollatorForTokenClassification(self.tokenizer)

        args = TrainingArguments(
            output_dir=str(output_dir),
            per_device_train_batch_size=per_device_train_batch_size,
            per_device_eval_batch_size=per_device_train_batch_size,
            num_train_epochs=num_train_epochs,
            save_strategy="epoch",
            save_total_limit=2,
            logging_steps=10,
            eval_strategy="epoch" if eval_dataset is not None else "no",
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

    def extract(self, text: str):
        return self.extract_batch([text])[0]

    def extract_batch(self, texts: list[str]):
        parsed = [words_and_offsets(text) for text in texts]
        encoded = [
            (words, *self._encode_words(words)) if words else None
            for words, _ in parsed
        ]

        non_empty = [item for item in encoded if item is not None]
        if not non_empty:
            return [None] * len(texts)

        pad_id = self.tokenizer.pad_token_id
        max_len = max(len(input_ids) for _, input_ids, _ in non_empty)

        batch_input_ids = [input_ids + [pad_id] * (max_len - len(input_ids)) for _, input_ids, _ in non_empty]
        batch_attention_mask = [[1] * len(input_ids) + [0] * (max_len - len(input_ids)) for _, input_ids, _ in non_empty]

        inputs = {
            "input_ids": torch.tensor(batch_input_ids),
            "attention_mask": torch.tensor(batch_attention_mask),
        }
        with torch.no_grad():
            logits = self.model(**inputs).logits
        pred_ids = logits.argmax(dim=-1).tolist()

        results_by_position = iter(zip(non_empty, pred_ids))
        results = []
        for item in encoded:
            if item is None:
                results.append(None)
                continue

            words, input_ids, word_index = item
            _, row_pred_ids = next(results_by_position)

            word_labels: list[str | None] = [None] * len(words)
            for pos, idx in enumerate(word_index):
                if idx != -1 and word_labels[idx] is None:
                    word_labels[idx] = self._id2label[row_pred_ids[pos]]

            results.append(self._decode(words, word_labels))

        return results

    def save(self, path: str | Path | None = None) -> None:
        path = path or self.MODEL_DIR
        Path(path).mkdir(parents=True, exist_ok=True)
        self.tokenizer.save_pretrained(path)
        self.model.save_pretrained(path)

    def push_to_hub(self, repo_id: str) -> None:
        self.tokenizer.push_to_hub(repo_id)
        self.model.push_to_hub(repo_id)

    @classmethod
    def load(cls, path: str | Path | None = None):
        path = path or cls.MODEL_DIR
        instance = cls.__new__(cls)
        instance.model_name = str(path)
        instance._label2id = {label: i for i, label in enumerate(cls.BIO_LABELS)}
        instance._id2label = {i: label for label, i in instance._label2id.items()}
        instance.tokenizer = AutoTokenizer.from_pretrained(path)
        instance.model = AutoModelForTokenClassification.from_pretrained(path)
        return instance
