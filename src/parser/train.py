"""
    The VM.AI parser model training scripts
    This script trains the AI for detecting tasks and other fields from a user input

    Module: parser
    Main dev: Vanea
    Written by (1): Vanea @ 07-03-2026
"""

import os
import json
import torch
from datasets import Dataset, concatenate_datasets, load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from huggingface_hub import snapshot_download
from yaml_parser import VMAI_YamlParser
import numpy as np
from data_generator import VMAI_DataGenerator

MAX_LIMIT = 100

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "distilbert-base-uncased"
    local_model_path = f"./models/{model_name}"
    os.makedirs("./models", exist_ok=True)

    if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
        print(f"Downloading {model_name}...")
        snapshot_download(repo_id=model_name, local_dir=local_model_path)
    else:
        print(f"Model already exists at {local_model_path}")

    parser = VMAI_YamlParser('data/VMAI_DataMain.yaml')
    parser.load_yaml()
    training_data = parser.parse()

    synthetic_dataset = VMAI_DataGenerator(training_data).generate(MAX_LIMIT)
    dataset = synthetic_dataset
    split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split_dataset["train"]
    test_dataset = split_dataset["test"]

    print(f"Training examples: {len(train_dataset)}")
    print(f"Test examples: {len(test_dataset)}")
    print(f"Labels: {training_data.label_list}")

    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

    # tokenization function
    def tokenize_function(examples):
        tokenized_inputs = tokenizer(
            examples["tokens"],
            truncation=True,
            is_split_into_words=True,
            padding="max_length",
            max_length=128
        )
        labels = []
        for i, label in enumerate(examples["labels"]):
            word_ids = tokenized_inputs.word_ids(batch_index=i)
            labels.append([
                -100 if word_idx is None else label[word_idx]
                for word_idx in word_ids
            ])
        tokenized_inputs["labels"] = labels
        return tokenized_inputs

    tokenized_train = train_dataset.map(tokenize_function, batched=True)
    tokenized_test = test_dataset.map(tokenize_function, batched=True)
    tokenized_train.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
    tokenized_test.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])

    # Load model or resume training if checkpoint exists
    output_dir = "./models/my_finetuned_task_planner"
    model = None
    if os.path.exists(output_dir) and os.listdir(output_dir):
        print("Resuming training from checkpoint...")
        model = AutoModelForTokenClassification.from_pretrained(output_dir)
    else:
        model = AutoModelForTokenClassification.from_pretrained(
            local_model_path,
            num_labels=len(training_data.label_list),
            id2label=training_data.id2label,
            label2id=training_data.label2id
        )
    model.to(device)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=128,
        per_device_eval_batch_size=128,
        num_train_epochs=3,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=10,
        save_total_limit=2,
        push_to_hub=False,
        remove_unused_columns=False,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        data_collator=data_collator
    )

    print("Starting training...")
    trainer.train()

    # save model & tokenizer
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    with open(os.path.join(output_dir, "label_mapping.json"), "w") as f:
        json.dump({
            "label_list": training_data.label_list,
            "label2id": training_data.label2id,
            "id2label": training_data.id2label
        }, f)

    print(f"Fine-tuned model saved to {output_dir}")
    print("Training completed!")

if __name__ == "__main__":
    main()