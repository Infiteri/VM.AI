"""
    The VM.AI parser model training scripts
    This script trains the AI for detecting tasks and other fields from a user input

    Module: parser
    Main dev: Vanea
    Written by (1): Vanea @ 07-03-2026
    Updated by: Vanea @ 19-03-2026 — split into functions, --mode flag, always resume
"""

import os
import argparse
import vars
import torch
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    T5ForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
from data_generator import VMAI_DataGenerator
from cfg import EnvConfig

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

DEFAULT_MODE = "both"


def download_base_model(cfg):
    os.makedirs(os.path.dirname(cfg.model_cache), exist_ok=True)
    if not os.path.exists(cfg.model_cache) or not os.listdir(cfg.model_cache):
        print("Downloading t5-small...")
        snapshot_download(repo_id="google-t5/t5-small", local_dir=cfg.model_cache)
    else:
        print(f"Model cached at {cfg.model_cache}")


def load_model(cfg, device):
    if os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir):
        print("Resuming from checkpoint...")
        return T5ForConditionalGeneration.from_pretrained(cfg.output_dir).to(device)
    print("No checkpoint found — starting from base model.")
    return T5ForConditionalGeneration.from_pretrained(cfg.model_cache).to(device)


def save_model(model, tokenizer, cfg):
    model.save_pretrained(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)
    print(f"Model saved to {cfg.output_dir}")


def load_synthetic_data(cfg):
    parser = VMAI_YamlParser(cfg.data_path)
    parser.load_yaml()
    return parser.parse()


def load_real_examples(cfg):
    if not os.path.exists(cfg.real_data_path):
        print("No real data file found — skipping real examples")
        return []
    real_parser = VMAI_RealDataParser(cfg.real_data_path)
    real_parser.load_yaml()
    examples = real_parser.parse()
    print(f"Real examples loaded: {len(examples)}")
    return examples


def build_dataset(cfg, mode):
    training_data = load_synthetic_data(cfg)

    if mode == "synthetic":
        real_examples = []
    else:
        real_examples = load_real_examples(cfg)

    if mode == "real":
        gen  = VMAI_DataGenerator(training_data, real_examples)
        data = {"input_text": [], "target_text": []}
        for example in real_examples:
            inp, tgt = gen._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        dataset = Dataset.from_dict(data)
    else:
        dataset = VMAI_DataGenerator(training_data, real_examples).generate(cfg.max_limit)

    split = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"Train : {len(split['train'])}  |  Test : {len(split['test'])}")
    return split["train"], split["test"]


def tokenize_datasets(train_dataset, test_dataset, tokenizer):
    def tokenize_function(examples):
        inputs  = tokenizer(examples["input_text"],  truncation=True, padding="max_length", max_length=256)
        targets = tokenizer(examples["target_text"], truncation=True, padding="max_length", max_length=256)
        labels  = [
            [(t if t != tokenizer.pad_token_id else -100) for t in label]
            for label in targets["input_ids"]
        ]
        inputs["labels"] = np.array(labels, dtype=np.int64)
        return inputs

    cols = ["input_ids", "attention_mask", "labels"]
    tok_train = train_dataset.map(tokenize_function, batched=True)
    tok_test  = test_dataset.map(tokenize_function,  batched=True)
    tok_train.set_format(type="torch", columns=cols)
    tok_test.set_format( type="torch", columns=cols)
    return tok_train, tok_test


def run_trainer(model, tokenizer, cfg, tok_train, tok_test, learning_rate):
    training_args = Seq2SeqTrainingArguments(
        output_dir=                     cfg.output_dir,
        eval_strategy=                  "epoch",
        save_strategy=                  "epoch",
        learning_rate=                  learning_rate,
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
    trainer = Seq2SeqTrainer(
        model=          model,
        args=           training_args,
        train_dataset=  tok_train,
        eval_dataset=   tok_test,
        data_collator=  DataCollatorForSeq2Seq(tokenizer, model=model),
    )
    print("Starting training...")
    trainer.train()


def parse_args():
    parser = argparse.ArgumentParser(description="VM.AI Parser Trainer")
    parser.add_argument(
        "--mode",
        choices=["both", "synthetic", "real"],
        default=DEFAULT_MODE,
        help="Data to train on: 'synthetic' | 'real' | 'both' (default)."
    )
    return parser.parse_args()


def main():
    args   = parse_args()
    cfg    = EnvConfig("local")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"Device     : {device}")
    print(f"Env        : {cfg.env}")
    print(f"Train mode : {args.mode}")

    os.makedirs(cfg.output_dir, exist_ok=True)
    download_base_model(cfg)

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_cache)
    model     = load_model(cfg, device)

    is_resume = os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir)
    lr        = cfg.learning_rate_resume if is_resume else cfg.learning_rate_fresh

    train_ds, test_ds   = build_dataset(cfg, args.mode)
    tok_train, tok_test = tokenize_datasets(train_ds, test_ds, tokenizer)

    run_trainer(model, tokenizer, cfg, tok_train, tok_test, lr)
    save_model(model, tokenizer, cfg)

    print("\nTraining completed!")


if __name__ == "__main__":
    main()