"""
    The VM.AI chat testing interface
"""

import torch
import re
import os
from transformers import AutoTokenizer, T5ForConditionalGeneration
from typing import Dict


class TaskPlannerPredictor:
    def __init__(self, model_path="./models/finetuned_parser"):
        print("Loading model...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = T5ForConditionalGeneration.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        print("✓ Model ready")

    def normalize(self, text: str):
        text = text.lower().strip()
        text = re.sub(r'(\d)(am|pm)', r'\1 \2', text)
        return text

    def predict(self, sentence: str) -> Dict:
        original_sentence = self.normalize(sentence)
        input_text = f"extract: {original_sentence}"

        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=128
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=64
            )

        output_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

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

        for part in output_text.split("|"):
            part = part.strip()
            if ":" in part:
                key, _, value = part.partition(":")
                key = key.strip().upper()
                value = value.strip()
                if key in raw and raw[key] is None:
                    raw[key] = value

        deadline = raw["DEADLINE"]
        if deadline is None and (raw["DATE"] or raw["TIME"]):
            deadline = " ".join(filter(None, [raw["DATE"], raw["TIME"]]))

        fixed_time = None
        if raw["TIME"]:
            fixed_time = bool(re.search(r'\bat\s+' + re.escape(raw["TIME"]), original_sentence))

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