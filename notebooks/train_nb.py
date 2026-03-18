"""
    The VM.AI parser model training scripts
    This script trains the AI for detecting tasks and other fields from a user input

    Module: parser
    Main dev: Vanea
    Written by (1): Vanea @ 07-03-2026
"""

import os
import vars
import torch
import numpy as np
from transformers import (
    AutoTokenizer,
    T5ForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser
from data_generator import VMAI_DataGenerator
from parser.cfg import EnvConfig

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

cfg = EnvConfig("local")  # <-- switch to "colab" when running on Colab


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Running in '{cfg.env}' mode")

    os.makedirs(os.path.dirname(cfg.model_cache), exist_ok=True)
    os.makedirs(cfg.output_dir, exist_ok=True)

    if not os.path.exists(cfg.model_cache) or not os.listdir(cfg.model_cache):
        print("Downloading t5-small...")
        snapshot_download(repo_id="google-t5/t5-small", local_dir=cfg.model_cache)
    else:
        print(f"Model already exists at {cfg.model_cache}")

    parser = VMAI_YamlParser(cfg.data_path)
    parser.load_yaml()
    training_data = parser.parse()

    synthetic_dataset = VMAI_DataGenerator(training_data).generate(cfg.max_limit)
    split_dataset = synthetic_dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split_dataset["train"]
    test_dataset = split_dataset["test"]

    print(f"Training examples: {len(train_dataset)}")
    print(f"Test examples: {len(test_dataset)}")

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_cache)

    def tokenize_function(examples):
        inputs = tokenizer(
            examples["input_text"],
            truncation=True,
            padding="max_length",
            max_length=128
        )
        targets = tokenizer(
            examples["target_text"],
            truncation=True,
            padding="max_length",
            max_length=128
        )
        labels = targets["input_ids"]
        labels = [
            [(token if token != tokenizer.pad_token_id else -100) for token in label]
            for label in labels
        ]
        inputs["labels"] = np.array(labels, dtype=np.int64)
        return inputs

    tokenized_train = train_dataset.map(tokenize_function, batched=True)
    tokenized_test = test_dataset.map(tokenize_function, batched=True)
    tokenized_train.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])
    tokenized_test.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

    if os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir):
        print("Resuming training from checkpoint...")
        model = T5ForConditionalGeneration.from_pretrained(cfg.output_dir)
    else:
        model = T5ForConditionalGeneration.from_pretrained(cfg.model_cache)
    model.to(device)

    training_args = Seq2SeqTrainingArguments(
        output_dir=                     cfg.output_dir,
        eval_strategy=                  "epoch",
        save_strategy=                  "epoch",
        learning_rate=                  2e-5,
        weight_decay=                   0.01,
        save_total_limit=               2,
        predict_with_generate=          True,
        push_to_hub=                    False,
        remove_unused_columns=          False,
        optim=                          "adafactor",
        num_train_epochs=               cfg.num_train_epochs,
        per_device_train_batch_size=    cfg.per_device_train_batch_size,
        per_device_eval_batch_size=     cfg.per_device_eval_batch_size,
        gradient_accumulation_steps=    cfg.gradient_accumulation_steps,
        fp16=                           cfg.fp16,
        dataloader_num_workers=         cfg.dataloader_num_workers,
        dataloader_pin_memory=          cfg.dataloader_pin_memory,
        logging_steps=                  cfg.logging_steps,
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        data_collator=data_collator
    )

    print("Starting training...")
    trainer.train()

    model.save_pretrained(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)

    print(f"Model saved to {cfg.output_dir}")
    print("Training completed!")


if __name__ == "__main__":
    main()