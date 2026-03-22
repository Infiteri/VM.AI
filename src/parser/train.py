"""
    VM.AI Parser — Training Script

    Written by: Vanea @ 07-03-2026
    Updated by: Vanea @ 21-03-2026 — full rewrite, local only, pipe format
    Updated by: Vanea @ 21-03-2026 — added specific mode
"""

import os
import time
import argparse
import torch
import numpy as np
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    T5ForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq,
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
from data_generator import DataGenerator
from cfg import Config

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def download_base_model(cfg):
    os.makedirs(cfg.model_cache, exist_ok=True)
    if not os.listdir(cfg.model_cache):
        print("Downloading t5-base...")
        snapshot_download(repo_id="google-t5/t5-base", local_dir=cfg.model_cache)
    else:
        print(f"Base model found at {cfg.model_cache}")


def load_model(cfg, device):
    if os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir):
        print("Resuming from checkpoint...")
        return T5ForConditionalGeneration.from_pretrained(cfg.output_dir).to(device)
    print("Starting from base model...")
    return T5ForConditionalGeneration.from_pretrained(cfg.model_cache).to(device)


def save_model(model, tokenizer, cfg):
    model.save_pretrained(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)
    print(f"Model saved to {cfg.output_dir}")


def build_dataset(cfg, mode):
    yp = VMAI_YamlParser(cfg.data_path)
    yp.load_yaml()
    training_data = yp.parse()

    real_examples = []
    if mode != "synthetic":
        if os.path.exists(cfg.real_data_path):
            rp = VMAI_RealDataParser(cfg.real_data_path)
            rp.load_yaml()
            real_examples = rp.parse()
            print(f"Real examples loaded: {len(real_examples)}")
        else:
            print("No real data file found — skipping")

    specific_examples = []
    if os.path.exists(cfg.specific_data_path):
        sp = VMAI_RealDataParser(cfg.specific_data_path)
        sp.load_yaml()
        specific_examples = sp.parse()
        print(f"Specific examples loaded: {len(specific_examples)}")
    else:
        print("No specific data file found — skipping")

    if mode == "specific":
        gen  = DataGenerator(training_data, real_examples, specific_examples)
        data = {"input_text": [], "target_text": []}
        for example in specific_examples:
            inp, tgt = gen._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        dataset = Dataset.from_dict(data)
    elif mode == "real":
        gen  = DataGenerator(training_data, real_examples, specific_examples)
        data = {"input_text": [], "target_text": []}
        for example in real_examples:
            inp, tgt = gen._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        dataset = Dataset.from_dict(data)
    else:
        dataset = DataGenerator(training_data, real_examples, specific_examples).generate(cfg.max_limit)

    split = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"Train: {len(split['train'])}  |  Test: {len(split['test'])}")
    return split["train"], split["test"]


def tokenize(train_ds, test_ds, tokenizer):
    def tokenize_fn(examples):
        inputs  = tokenizer(examples["input_text"],  truncation=True, padding="max_length", max_length=256)
        targets = tokenizer(examples["target_text"], truncation=True, padding="max_length", max_length=64)
        labels  = [
            [(t if t != tokenizer.pad_token_id else -100) for t in label]
            for label in targets["input_ids"]
        ]
        inputs["labels"] = np.array(labels, dtype=np.int64)
        return inputs

    cols = ["input_ids", "attention_mask", "labels"]
    tok_train = train_ds.map(tokenize_fn, batched=True).with_format("torch", columns=cols)
    tok_test  = test_ds.map(tokenize_fn,  batched=True).with_format("torch", columns=cols)
    return tok_train, tok_test


def train(model, tokenizer, cfg, tok_train, tok_test, lr):
    args = Seq2SeqTrainingArguments(
        output_dir=                  cfg.output_dir,
        eval_strategy=               "epoch",
        save_strategy=               "epoch",
        learning_rate=               lr,
        weight_decay=                0.01,
        save_total_limit=            2,
        predict_with_generate=       True,
        push_to_hub=                 False,
        remove_unused_columns=       False,
        optim=                       "adafactor",
        num_train_epochs=            cfg.num_train_epochs,
        per_device_train_batch_size= cfg.per_device_train_batch_size,
        per_device_eval_batch_size=  cfg.per_device_eval_batch_size,
        gradient_accumulation_steps= cfg.gradient_accumulation_steps,
        fp16=                        cfg.fp16,
        dataloader_num_workers=      cfg.dataloader_num_workers,
        dataloader_pin_memory=       cfg.dataloader_pin_memory,
        logging_steps=               cfg.logging_steps,
    )
    trainer = Seq2SeqTrainer(
        model=         model,
        args=          args,
        train_dataset= tok_train,
        eval_dataset=  tok_test,
        data_collator= DataCollatorForSeq2Seq(tokenizer, model=model),
    )
    print("Starting training...")
    trainer.train()


def parse_args():
    parser = argparse.ArgumentParser(description="VM.AI Parser Trainer")
    parser.add_argument("--mode", choices=["both", "synthetic", "real", "specific"], default="both")
    return parser.parse_args()


def main():
    start = time.time()
    args  = parse_args()
    cfg   = Config()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"Device : {device}")
    print(f"Mode   : {args.mode}")

    os.makedirs(cfg.output_dir, exist_ok=True)
    download_base_model(cfg)

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_cache)
    model     = load_model(cfg, device)

    is_resume = os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir)
    lr        = cfg.learning_rate_resume if is_resume else cfg.learning_rate_fresh

    train_ds, test_ds   = build_dataset(cfg, args.mode)
    tok_train, tok_test = tokenize(train_ds, test_ds, tokenizer)

    train(model, tokenizer, cfg, tok_train, tok_test, lr)
    save_model(model, tokenizer, cfg)

    elapsed = int(time.time() - start)
    h, rem  = divmod(elapsed, 3600)
    m, s    = divmod(rem, 60)
    print(f"\nDone in {h:02d}h {m:02d}m {s:02d}s")


if __name__ == "__main__":
    main()