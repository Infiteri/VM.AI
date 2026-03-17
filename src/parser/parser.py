"""
    The VM.AI parser module responsible for training and parsing user input into neat code-defined structure

    Module: parser
    Main dev: Vanea
    Written by: Vanea @ 10-03-2026
"""

import os
import re
import json
import torch
import vars
from typing import Dict
from transformers import AutoTokenizer, AutoModelForTokenClassification

# parser, todo: ENSURE MODEL GETS LOADED ONCE WHEN BACKEND IS STARTED
class TaskPlannerPredictor:
    def __init__(self, model_path=f"./models/{vars.PARSER_MODEL_NAME}"):
        print("Loading model...")
        label_mapping_path = os.path.join(model_path, "label_mapping.json")
        if os.path.exists(label_mapping_path):
            with open(label_mapping_path, "r") as f:
                mapping = json.load(f)

            self.label_list = mapping["label_list"]
            self.label2id = mapping["label2id"]
            self.id2label = {int(k): v for k, v in mapping["id2label"].items()}
        else:
            raise RuntimeError("label_mapping.json missing")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path,
            num_labels=len(self.label_list),
            id2label=self.id2label,
            label2id=self.label2id
        )
        self.model.to(self.device)
        self.model.eval()

    def normalize(self, text: str):
        text = text.lower().strip()
        text = re.sub(r'(\d)(am|pm)', r'\1 \2', text)
        return text

    def predict(self, sentence: str) -> Dict:
        original_sentence = self.normalize(sentence)
        tokens = original_sentence.split()
        encoding = self.tokenizer(
            tokens,
            is_split_into_words=True,
            truncation=True,
            return_tensors="pt",
            padding="max_length",
            max_length=128
        )

        word_ids = encoding.word_ids()
        inputs = {k: v.to(self.device) for k, v in encoding.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().numpy()
        entities = []
        current_entity = None
        current_tokens = []
        seen_words = set()

        for i, word_idx in enumerate(word_ids):
            if word_idx is None:
                continue
            if word_idx in seen_words:
                continue
            seen_words.add(word_idx)

            label = self.id2label[predictions[i]]
            word = tokens[word_idx]

            if label.startswith("B-"):
                if current_entity:
                    entities.append((current_entity, " ".join(current_tokens)))
                current_entity = label[2:]
                current_tokens = [word]
            elif label.startswith("I-") and current_entity == label[2:]:
                current_tokens.append(word)
            else:
                if current_entity:
                    entities.append((current_entity, " ".join(current_tokens)))
                current_entity = None
                current_tokens = []

        if current_entity:
            entities.append((current_entity, " ".join(current_tokens)))

        # --- collect raw extracted values ---
        raw = {
            "TASK": None,
            "DEADLINE": None,
            "DATE": None,
            "TIME": None,
            "DURATION": None,
            "LOCATION": None,
            "PRIORITY": None,
            "DIFFICULTY": None,
            "CATEGORY": None,
        }

        for ent_type, text in entities:
            ent_type = ent_type.upper()
            if ent_type in raw and raw[ent_type] is None:
                raw[ent_type] = text

        # --- derive deadline from DATE + TIME if no explicit DEADLINE tagged ---
        deadline = raw["DEADLINE"]
        if deadline is None and (raw["DATE"] or raw["TIME"]):
            deadline = " ".join(filter(None, [raw["DATE"], raw["TIME"]]))

        # --- derive fixed_time: True only if TIME was extracted AND 'at <time>' pattern present ---
        fixed_time = None
        if raw["TIME"]:
            if re.search(r'\bat\s+' + re.escape(raw["TIME"]), original_sentence):
                fixed_time = True
            else:
                fixed_time = False

        return {
            "name":       raw["TASK"],
            "deadline":   deadline,
            "difficulty": raw["DIFFICULTY"],
            "duration":   raw["DURATION"],
            "category":   raw["CATEGORY"],
            "location":   raw["LOCATION"],
            "importance": raw["PRIORITY"],
            "fixed_time": fixed_time,
        }


# todo: TEST
def parse_input_to_json(input):
    pr = TaskPlannerPredictor()
    return pr.predict(input)