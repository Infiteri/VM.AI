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
from transformers import AutoTokenizer, T5ForConditionalGeneration

class TaskPlannerPredictor:
    def __init__(self, model_path=f"./models/{vars.PARSER_MODEL_NAME}"):
        print("Loading model...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = T5ForConditionalGeneration.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()

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


def parse_input_to_json(input):
    pr = TaskPlannerPredictor()
    return pr.predict(input)