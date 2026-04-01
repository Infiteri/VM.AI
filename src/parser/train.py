"""
    VM.AI Parser — Training Script

    Written by: Vanea @ 07-03-2026
    Updated by: Vanea @ 21-03-2026 — full rewrite, local only, pipe format
    Updated by: Vanea @ 21-03-2026 — added specific mode
    Updated by: Vanea @ 25-03-2026 — compute_metrics, target length fix, Windows fix
    Updated by: Vanea @ 01-04-2026 — added modify_only mode
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
    EvalPrediction,
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
from data_generator import DataGenerator
from cfg import Config

if os.name != "nt":
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

TRACKED_FIELDS = [
    "name", "deadline", "difficulty", "importance",
    "duration", "category", "location",
    "fixed_time", "fixed_start", "recurrent", "recurrence_days",
]


def _parse_pipe(text: str) -> dict:
    result = {}
    for part in text.split("|"):
        part = part.strip()
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k, v = k.strip().lower(), v.strip().lower()
        if v in ("null", ""):
            v = None
        result[k] = v
    return result


def compute_metrics(eval_preds: EvalPrediction, tokenizer):
    predictions, label_ids = eval_preds

    predictions = np.where(predictions < 0, tokenizer.pad_token_id, predictions)
    label_ids   = np.where(label_ids   < 0, tokenizer.pad_token_id, label_ids)

    decoded_preds  = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(label_ids,   skip_special_tokens=True)

    correct = {f: 0 for f in TRACKED_FIELDS}
    present = {f: 0 for f in TRACKED_FIELDS}

    for pred_str, label_str in zip(decoded_preds, decoded_labels):
        pred_dict  = _parse_pipe(pred_str)
        label_dict = _parse_pipe(label_str)
        for field in TRACKED_FIELDS:
            if field not in label_dict:
                continue
            present[field] += 1
            if pred_dict.get(field) == label_dict[field]:
                correct[field] += 1

    metrics = {}
    total_correct = 0
    total_present = 0
    for field in TRACKED_FIELDS:
        n = present[field]
        c = correct[field]
        acc = round(c / n, 4) if n > 0 else 0.0
        metrics[f"acc_{field}"] = acc
        total_correct += c
        total_present += n

    metrics["acc_overall"] = round(total_correct / total_present, 4) if total_present > 0 else 0.0
    return metrics


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
            try:
                rp = VMAI_RealDataParser(cfg.real_data_path)
                rp.load_yaml()
                real_examples = rp.parse()
                print(f"Real examples loaded: {len(real_examples)}")
            except Exception as e:
                print(f"Real data skipped — failed to load: {e}")
        else:
            print("No real data file found — skipping")

    specific_examples = []
    if os.path.exists(cfg.specific_data_path):
        try:
            sp = VMAI_RealDataParser(cfg.specific_data_path)
            sp.load_yaml()
            specific_examples = sp.parse()
            print(f"Specific examples loaded: {len(specific_examples)}")
        except Exception as e:
            print(f"Specific data skipped — failed to load: {e}")
    else:
        print("No specific data file found — skipping")

    gen = DataGenerator(training_data, real_examples, specific_examples)

    # ── mode routing ──────────────────────────────────────────────────────────
    if mode == "modify_only":
        dataset = gen.generate_modify_only(cfg.max_limit)

    elif mode == "specific":
        data = {"input_text": [], "target_text": []}
        for example in specific_examples:
            inp, tgt = gen._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        dataset = Dataset.from_dict(data)

    elif mode == "real":
        data = {"input_text": [], "target_text": []}
        for example in real_examples:
            inp, tgt = gen._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        dataset = Dataset.from_dict(data)

    else:
        dataset = gen.generate(cfg.max_limit)

    split = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"Train: {len(split['train'])}  |  Test: {len(split['test'])}")
    return split["train"], split["test"]


def tokenize(train_ds, test_ds, tokenizer):
    def tokenize_fn(examples):
        inputs  = tokenizer(
            examples["input_text"],
            truncation=True, padding="max_length", max_length=256,
        )
        targets = tokenizer(
            examples["target_text"],
            truncation=True, padding="max_length", max_length=128,
        )
        labels = np.array([
            [(t if t != tokenizer.pad_token_id else -100) for t in label]
            for label in targets["input_ids"]
        ], dtype=np.int64)
        inputs["labels"] = labels
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
        generation_max_length=       128,
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
        model=           model,
        args=            args,
        train_dataset=   tok_train,
        eval_dataset=    tok_test,
        data_collator=   DataCollatorForSeq2Seq(tokenizer, model=model),
        compute_metrics= lambda p: compute_metrics(p, tokenizer),
    )

    print("Starting training...")
    trainer.train()


def parse_args():
    parser = argparse.ArgumentParser(description="VM.AI Parser Trainer")
    parser.add_argument(
        "--mode",
        choices=["both", "synthetic", "real", "specific", "modify_only"],
        default="both",
        help=(
            "both/synthetic/real/specific = standard modes. "
            "modify_only = targeted fine-tune on modify examples only "
            "(requires an existing checkpoint)."
        ),
    )
    return parser.parse_args()


def main():
    start  = time.time()
    args   = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg    = Config(args.mode)

    if args.mode == "modify_only":
        if not os.path.exists(cfg.output_dir) or not os.listdir(cfg.output_dir):
            print("ERROR: modify_only requires an existing trained checkpoint.")
            print(f"       Nothing found at: {cfg.output_dir}")
            print("       Train with --mode both (or synthetic) first.")
            return

    print(f"Device : {device}")
    print(f"Mode   : {args.mode}")
    print(f"Epochs : {cfg.num_train_epochs}")

    is_resume = os.path.exists(cfg.output_dir) and os.listdir(cfg.output_dir)
    lr = cfg.learning_rate_resume if is_resume else cfg.learning_rate_fresh
    print(f"Resume : {is_resume}  LR: {lr}")

    os.makedirs(cfg.output_dir, exist_ok=True)
    download_base_model(cfg)

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_cache)
    model     = load_model(cfg, device)

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