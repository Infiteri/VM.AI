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

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

MAX_LIMIT = 10000

# All paths relative to Drive root where train.py lives
BASE_DIR = '/content/drive/MyDrive'
DRIVE_OUTPUT = f'{BASE_DIR}/models/{vars.PARSER_MODEL_NAME}'
DATA_PATH = f'{BASE_DIR}/data/{vars.SYNTHETIC_DATASET_PATH}'
MODEL_CACHE = f'{BASE_DIR}/models/google-t5/t5-small'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

model_name = "google-t5/t5-small"
os.makedirs(f'{BASE_DIR}/models', exist_ok=True)

if not os.path.exists(MODEL_CACHE) or not os.listdir(MODEL_CACHE):
    print(f"Downloading {model_name}...")
    snapshot_download(repo_id=model_name, local_dir=MODEL_CACHE)
else:
    print(f"Model already exists at {MODEL_CACHE}")

parser = VMAI_YamlParser(DATA_PATH)
parser.load_yaml()
training_data = parser.parse()

synthetic_dataset = VMAI_DataGenerator(training_data).generate(MAX_LIMIT)
split_dataset = synthetic_dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split_dataset["train"]
test_dataset = split_dataset["test"]

print(f"Training examples: {len(train_dataset)}")
print(f"Test examples: {len(test_dataset)}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_CACHE)

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
tokenized_train.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])
tokenized_test.set_format(type='torch', columns=['input_ids', 'attention_mask', 'labels'])

os.makedirs(DRIVE_OUTPUT, exist_ok=True)

if os.path.exists(DRIVE_OUTPUT) and os.listdir(DRIVE_OUTPUT):
    print("Resuming training from checkpoint...")
    model = T5ForConditionalGeneration.from_pretrained(DRIVE_OUTPUT)
else:
    model = T5ForConditionalGeneration.from_pretrained(MODEL_CACHE)
model.to(device)

# TODO: DIFFERENT PARAMS FOR COLAB
training_args = Seq2SeqTrainingArguments(
    output_dir=DRIVE_OUTPUT,
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    save_total_limit=2,
    predict_with_generate=True,
    push_to_hub=False,
    remove_unused_columns=False,
    gradient_accumulation_steps=16,
    fp16=True,
    dataloader_num_workers=2,
    dataloader_pin_memory=True,
    optim="adafactor",
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

model.save_pretrained(DRIVE_OUTPUT)
tokenizer.save_pretrained(DRIVE_OUTPUT)

print(f"Model saved to {DRIVE_OUTPUT}")
print("Training completed!")