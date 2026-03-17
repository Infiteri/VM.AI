"""
    The VM.AI chat testing interface
"""

import torch
import json
import os
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification
from typing import Dict


class TaskPlannerPredictor:
    def __init__(self, model_path="./models/finetuned_parser"):
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
        print("✓ Model ready")

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

        deadline = raw["DEADLINE"]
        if deadline is None and (raw["DATE"] or raw["TIME"]):
            deadline = " ".join(filter(None, [raw["DATE"], raw["TIME"]]))

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


def format_output(results: Dict):
    parts = []

    if results["name"]:
        parts.append(f"📋 name       : {results['name']}")
    if results["deadline"]:
        parts.append(f"📅 deadline   : {results['deadline']}")
    if results["difficulty"]:
        parts.append(f"💪 difficulty : {results['difficulty']}")
    if results["duration"]:
        parts.append(f"⏱️ duration   : {results['duration']}")
    if results["category"]:
        parts.append(f"🏷️ category   : {results['category']}")
    if results["location"]:
        parts.append(f"📍 location   : {results['location']}")
    if results["importance"]:
        parts.append(f"⚡ importance : {results['importance']}")
    if results["fixed_time"] is not None:
        parts.append(f"📌 fixed_time : {results['fixed_time']}")

    if not parts:
        return " → ❌ Nothing extracted"

    return "\n   " + "\n   ".join(parts)


def main():
    print("\n" + "=" * 60)
    print("🗓️ TASK PLANNER CHAT")
    print("=" * 60)

    predictor = TaskPlannerPredictor()
    print("\nType 'end' to exit")
    count = 0

    while True:
        user_input = input(f"\n{count+1:2d} > ").strip()

        if user_input.lower() == "end":
            print("\nProcessed", count, "sentences")
            break

        if not user_input:
            continue

        try:
            results = predictor.predict(user_input)
            print(format_output(results))
            count += 1
        except Exception as e:
            print("Prediction error:", e)


if __name__ == "__main__":
    main()