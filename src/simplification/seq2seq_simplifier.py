import json
from pathlib import Path

import torch
from datasets import Dataset
from huggingface_hub import hf_hub_download
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    PreTrainedTokenizerFast,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from transformers.trainer_utils import get_last_checkpoint

DEFAULT_MODEL_NAME = "VietAI/vit5-base"
MAX_INPUT_LENGTH = 256
MAX_TARGET_LENGTH = 384
SENTENCE_SEPARATOR = " <sep> "


def _load_tokenizer(model_name: str):
    try:
        return AutoTokenizer.from_pretrained(model_name)
    except TypeError:
        # Một số checkpoint T5 cũ (vd. VietAI/vit5-base) chỉ ship spiece.model,
        # và bước convert sentencepiece -> fast tokenizer bị lỗi với bản `tokenizers`
        # hiện tại (TypeError trong Unigram(vocab=...)). Các repo này có sẵn
        # tokenizer.json đã convert từ trước, nên bypass converter, load thẳng từ đó.
        tokenizer_file = hf_hub_download(model_name, "tokenizer.json")
        special_tokens_file = hf_hub_download(model_name, "special_tokens_map.json")
        special_tokens = json.loads(Path(special_tokens_file).read_text(encoding="utf-8"))
        return PreTrainedTokenizerFast(tokenizer_file=tokenizer_file, **special_tokens)


class Seq2SeqSimplifier:
    """Tách câu phức thành nhiều câu đơn bằng seq2seq fine-tune (ViT5/BARTpho)."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.tokenizer = _load_tokenizer(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def _tokenize(self, examples: dict) -> dict:
        model_inputs = self.tokenizer(
            examples["complex"], max_length=MAX_INPUT_LENGTH, truncation=True
        )
        labels = self.tokenizer(
            text_target=examples["simple"], max_length=MAX_TARGET_LENGTH, truncation=True
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    def fit(
        self,
        train_pairs: list[tuple[str, str]],
        eval_pairs: list[tuple[str, str]] | None = None,
        output_dir: str | Path = "models/simplifier",
        num_train_epochs: int = 20,
        per_device_train_batch_size: int = 4,
        early_stopping_patience: int = 3,
        resume: bool = True,
    ) -> Seq2SeqTrainer:
        """num_train_epochs là mức trần; nếu có eval_pairs, training tự dừng sớm
        khi eval_loss không cải thiện sau `early_stopping_patience` lần eval liên tiếp,
        thay vì phải đoán trước số epoch tối ưu."""
        train_dataset = self._to_dataset(train_pairs)
        eval_dataset = self._to_dataset(eval_pairs) if eval_pairs else None

        collator = DataCollatorForSeq2Seq(self.tokenizer, model=self.model)

        args = Seq2SeqTrainingArguments(
            output_dir=str(output_dir),
            per_device_train_batch_size=per_device_train_batch_size,
            per_device_eval_batch_size=per_device_train_batch_size,
            num_train_epochs=num_train_epochs,
            predict_with_generate=True,
            generation_max_length=MAX_TARGET_LENGTH,
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

        callbacks = [EarlyStoppingCallback(early_stopping_patience=early_stopping_patience)] if eval_dataset is not None else []

        trainer = Seq2SeqTrainer(
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

    def _to_dataset(self, pairs: list[tuple[str, str]]) -> Dataset:
        dataset = Dataset.from_dict({
            "complex": [complex_ for complex_, _ in pairs],
            "simple": [simple for _, simple in pairs],
        })
        return dataset.map(self._tokenize, batched=True, remove_columns=["complex", "simple"])

    def simplify(self, text: str) -> list[str]:
        inputs = self.tokenizer(text, max_length=MAX_INPUT_LENGTH, truncation=True, return_tensors="pt")
        output_ids = self.model.generate(**inputs, max_length=MAX_TARGET_LENGTH)
        decoded = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return [s.strip() for s in decoded.split(SENTENCE_SEPARATOR.strip()) if s.strip()]

    def save(self, path: str | Path) -> None:
        self.tokenizer.save_pretrained(path)
        self.model.save_pretrained(path)

    def push_to_hub(self, repo_id: str) -> None:
        self.tokenizer.push_to_hub(repo_id)
        self.model.push_to_hub(repo_id)

    @classmethod
    def load(cls, path: str | Path) -> "Seq2SeqSimplifier":
        instance = cls.__new__(cls)
        instance.model_name = str(path)
        instance.tokenizer = _load_tokenizer(path)
        instance.model = AutoModelForSeq2SeqLM.from_pretrained(path)
        return instance
