# train_lazy.py
import os
import random
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from huggingface_hub import snapshot_download

print("Starting training script...")

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

    print("Generating synthetic training data...")
    label_list = ["O", "B-TASK", "I-TASK", "B-DURATION", "I-DURATION", "B-DEADLINE", "I-DEADLINE"]
    label2id = {label: i for i, label in enumerate(label_list)}
    id2label = {i: label for label, i in label2id.items()}

    templates = [
        "I need to [TASK] for [DURATION] [DEADLINE]",
        "Remind me to [TASK] at [DEADLINE]",
        "Schedule [TASK] for [DURATION] before [DEADLINE]",
    ]
    tasks = ["buy milk", "study math", "call mom", "finish report", "workout", "read a book"]
    durations = ["2 hours", "30 minutes", "1 hour", "90 minutes", "3 hours"]
    deadlines = ["tomorrow", "at 5pm", "next Monday", "by Friday", "today at noon", "this evening"]

    data = {"tokens": [], "labels": []}
    for _ in range(1000):
        template = random.choice(templates)
        task = random.choice(tasks)
        duration = random.choice(durations)
        deadline = random.choice(deadlines)

        sentence = template.replace("[TASK]", task).replace("[DURATION]", duration).replace("[DEADLINE]", deadline)
        tokens = sentence.split()
        labels = ["O"] * len(tokens)

        # Helper function to label token sequences
        def assign_labels(seq, prefix):
            seq_tokens = seq.split()
            for i in range(len(tokens) - len(seq_tokens) + 1):
                if tokens[i:i + len(seq_tokens)] == seq_tokens:
                    labels[i] = f"B-{prefix}"
                    for j in range(1, len(seq_tokens)):
                        labels[i + j] = f"I-{prefix}"
                    break

        assign_labels(task, "TASK")
        assign_labels(duration, "DURATION")
        assign_labels(deadline, "DEADLINE")

        data["tokens"].append(tokens)
        data["labels"].append([label2id[l] for l in labels])

    dataset = Dataset.from_dict(data)
    split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split_dataset["train"]
    test_dataset = split_dataset["test"]

    print(f"Training examples: {len(train_dataset)}")
    print(f"Test examples: {len(test_dataset)}")

    tokenizer = AutoTokenizer.from_pretrained(local_model_path)

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

    model = AutoModelForTokenClassification.from_pretrained(
        local_model_path,
        num_labels=len(label_list),
        id2label=id2label,
        label2id=label2id
    )
    model.to(device)

    training_args = TrainingArguments(
        output_dir="./results",
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
        dataloader_num_workers=0,
        remove_unused_columns=False
    )

    data_collator = DataCollatorForTokenClassification(tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        data_collator=data_collator,
    )

    print("Starting training...")
    trainer.train()

    output_dir = "./models/my_finetuned_task_planner"
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    with open(os.path.join(output_dir, "label_mapping.json"), "w") as f:
        json.dump({"label_list": label_list, "label2id": label2id, "id2label": id2label}, f)

    print(f"Fine-tuned model saved to {output_dir}")
    print("Training completed successfully!")

if __name__ == "__main__":
    main()