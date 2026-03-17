"""
    The VM.AI parser model training scripts
    This script trains the AI for detecting tasks and other fields from a user input

    Module: parser
    Main dev: Vanea
    Written by (1): Vanea @ 07-03-2026
"""

import os
import vars
import json
import torch
from datasets import Dataset, concatenate_datasets, load_dataset
from transformers import (
    AutoTokenizer,
    T5ForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser
import numpy as np
from data_generator import VMAI_DataGenerator

MAX_LIMIT = 100000

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "google-t5/t5-small"
    local_model_path = f"./models/{model_name}"
    os.makedirs("./models", exist_ok=True)

    if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
        print(f"Downloading {model_name}...")
        snapshot_download(repo_id=model_name, local_dir=local_model_path)
    else:
        print(f"Model already exists at {local_model_path}")

    parser = VMAI_YamlParser(f'./data/{vars.SYNTHETIC_DATASET_PATH}')
    parser.load_yaml()
    training_data = parser.parse()

    synthetic_dataset = VMAI_DataGenerator(training_data).generate(MAX_LIMIT)
    dataset = synthetic_dataset
    split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split_dataset["train"]
    test_dataset = split_dataset["test"]

    print(f"Training examples: {len(train_dataset)}")
    print(f"Test examples: {len(test_dataset)}")

    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

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
        inputs["labels"] = np.array(labels, dtype=np.int64)  # add this line, was just labels
        return inputs

    tokenized_train = train_dataset.map(tokenize_function, batched=True)
    tokenized_test = test_dataset.map(tokenize_function, batched=True)
    tokenized_train.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
    tokenized_test.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])

    output_dir = f"./models/{vars.PARSER_MODEL_NAME}"
    model = None
    if os.path.exists(output_dir) and os.listdir(output_dir):
        print("Resuming training from checkpoint...")
        model = T5ForConditionalGeneration.from_pretrained(output_dir)
    else:
        model = T5ForConditionalGeneration.from_pretrained(local_model_path)
    model.to(device)

    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,       # safe for 8GB with T5
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        save_total_limit=2,
        predict_with_generate=True,
        push_to_hub=False,
        remove_unused_columns=False,
        gradient_accumulation_steps=16,      # effective batch = 128
        fp16=True,                           # ~halves VRAM, speeds up training
        dataloader_num_workers=4,            # parallel data loading off GPU
        dataloader_pin_memory=True,          # faster CPU→GPU transfer
        optim="adafactor",                   # T5's native optimizer, uses far less VRAM than AdamW
        logging_steps=10,
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

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"Fine-tuned model saved to {output_dir}")
    print("Training completed!")


os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
if __name__ == "__main__":
    main()