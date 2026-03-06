# train.py
import os
import random
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

# -------------------------------
# GLOBAL SETTINGS
# -------------------------------
MAX_LIMIT = 50000  # Max number of synthetic examples

# -------------------------------
# Synthetic data generation
# -------------------------------
def generate_synthetic_data(training_data, max_examples=MAX_LIMIT):
    all_placeholders = {
        "TASK": training_data.tasks,
        "DURATION": training_data.durations,
        "DEADLINE": training_data.deadlines,
        "PERSON": training_data.persons,
        "LOCATION": training_data.locations,
        "DATE": training_data.dates,
        "TIME": training_data.times,
        "PRIORITY": training_data.priorities,
        "PROJECT": training_data.projects,
        "MEETING": training_data.meetings,
        "COST": training_data.costs,
        "QUANTITY": training_data.quantities,
        "CONTACT": training_data.contacts,
        "EMAIL": training_data.emails,
        "PHONE": training_data.phones,
        "RECURRENCE": training_data.recurrences
    }

    templates = training_data.templates
    num_examples = min(max_examples, 999999999)  # will limit below

    # estimate total possible combinations
# estimate total possible combinations
    total_combinations = len(templates) * np.prod([len(opts) if opts else 1 for opts in all_placeholders.values()])
    total_combinations = int(total_combinations)

    if total_combinations < max_examples:
        print(f"Total possible combinations: {total_combinations}, generating: {total_combinations}")
        num_examples = total_combinations
    else:
        print(f"Total possible combinations: {total_combinations}, generating: {max_examples}")
        num_examples = max_examples

    data = {"tokens": [], "labels": []}

    for i in range(num_examples):
        if i % 10000 == 0 and i > 0:
            print(f"Generated {i}/{num_examples} examples")

        # pick random template
        template = random.choice(templates)
        sentence = template
        placeholder_map = {}

        # replace placeholders
        for ph, options in all_placeholders.items():
            if f"[{ph}]" in sentence and options:
                value = str(random.choice(options))
                sentence = sentence.replace(f"[{ph}]", value)
                placeholder_map[value] = ph

        # tokenize and assign labels
        tokens = sentence.split()
        labels = ["O"] * len(tokens)

        for entity_text, entity_type in placeholder_map.items():
            entity_tokens = entity_text.split()
            for j in range(len(tokens) - len(entity_tokens) + 1):
                if tokens[j:j + len(entity_tokens)] == entity_tokens:
                    labels[j] = f"B-{entity_type}"
                    for k in range(1, len(entity_tokens)):
                        labels[j + k] = f"I-{entity_type}"
                    break

        data["tokens"].append(tokens)
        data["labels"].append([training_data.label2id.get(l, 0) for l in labels])

    return Dataset.from_dict(data)

# -------------------------------
# Main training
# -------------------------------
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "distilbert-base-uncased"
    local_model_path = f"./models/{model_name}"
    os.makedirs("./models", exist_ok=True)

    # download Hugging Face model if not exists
    if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
        print(f"Downloading {model_name}...")
        snapshot_download(repo_id=model_name, local_dir=local_model_path)
    else:
        print(f"Model already exists at {local_model_path}")

    # load YAML data
    print("Loading YAML training data...")
    parser = VMAI_YamlParser('data/VMAI_DataMain.yaml')
    parser.load_yaml()
    training_data = parser.parse()

    # generate synthetic dataset
    synthetic_dataset = generate_synthetic_data(training_data, max_examples=MAX_LIMIT)

    # optional: load additional real NER datasets
    try:
        conll = load_dataset("conll2003", split="train[:5000]")
        print(f"Loaded CoNLL-2003: {len(conll)} examples")
        dataset = concatenate_datasets([synthetic_dataset, conll])
    except Exception as e:
        print("Couldn't load CoNLL-2003:", e)
        dataset = synthetic_dataset

    # train/test split
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
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
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