"""
    The VM.AI parser module responsible for parsing user input into structured task schema

    Module: parser
    Main dev: Vanea
    Written by: Vanea @ 10-03-2026
    Updated by: Vanea @ 21-03-2026 — pipe format output, _pipe_to_schema reconstruction
"""

import os
import re
import json
import torch
import vars
from typing import Dict
from transformers import AutoTokenizer, T5ForConditionalGeneration


PREDICTED_FIELDS = {"difficulty", "duration", "category", "location", "importance", "start"}

ALL_FIELDS = {
    "name":            None,
    "start":           None,
    "deadline":        None,
    "difficulty":      None,
    "duration":        None,
    "category":        None,
    "location":        None,
    "importance":      None,
    "fixed_time":      False,
    "fixed_start":     None,
    "recurrent":       False,
    "recurrence_days": None,
}


class TaskPlannerPredictor:
    def __init__(self, model_path=f"./models/{vars.PARSER_MODEL_NAME}"):
        print("Loading model...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = T5ForConditionalGeneration.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"✓ Model ready ({self.device})")

    def normalize(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r'(\d)(am|pm)', r'\1 \2', text)
        return text

    def _run_model(self, input_text: str) -> str:
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=256
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=128
            )

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

    def _pipe_to_schema(self, flat_str: str) -> Dict:
        raw = {}
        for part in flat_str.split("|"):
            part = part.strip()
            if "=" not in part:
                continue
            k, _, v = part.partition("=")
            k, v = k.strip(), v.strip()
            if v.lower() == "null":   v = None
            elif v.lower() == "true":  v = True
            elif v.lower() == "false": v = False
            raw[k] = v

        schema = {}
        for field, default in ALL_FIELDS.items():
            val = raw.get(field, default)
            schema[field] = {
                "value":     val,
                "predicted": field in PREDICTED_FIELDS
            }
        return schema

    def _parse_output(self, output_text: str) -> Dict:
        if "=" in output_text:
            result = self._pipe_to_schema(output_text)
            if result.get("name", {}).get("value"):
                return result
        return {"error": "parse_failed", "raw": output_text}

    def predict_add(self, sentence: str) -> Dict:
        input_text  = f"add: {self.normalize(sentence)}"
        output_text = self._run_model(input_text)
        return self._parse_output(output_text)

    def predict_modify(self, existing_task: Dict, change_prompt: str) -> Dict:
        existing_summary = {
            k: v["value"] if isinstance(v, dict) else v
            for k, v in existing_task.items()
            if (v["value"] if isinstance(v, dict) else v) is not None
        }
        input_text  = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} \u2502 {self.normalize(change_prompt)}"
        output_text = self._run_model(input_text)

        changed = {}
        for part in output_text.split("|"):
            part = part.strip()
            if "=" not in part:
                continue
            k, _, v = part.partition("=")
            k, v = k.strip(), v.strip()
            if v.lower() == "null":   v = None
            elif v.lower() == "true":  v = True
            elif v.lower() == "false": v = False
            if k:
                changed[k] = {"value": v, "predicted": False}

        if not changed:
            return {"error": "parse_failed", "raw": output_text}

        return changed


def parse_input_to_json(sentence: str) -> Dict:
    pr = TaskPlannerPredictor()
    return pr.predict_add(sentence)


# ─── Testing ──────────────────────────────────────────────────────────────────

def format_output(result: Dict):
    if "error" in result:
        return f"   ❌ parse failed\n   raw: {result['raw']}"
    if not result:
        return "   ❌ nothing extracted"

    icons = {
        "name": "📋", "start": "🕐", "deadline": "📅",
        "difficulty": "💪", "duration": "⏱️", "category": "🏷️",
        "location": "📍", "importance": "⚡", "fixed_time": "📌",
        "fixed_start": "🔒", "recurrent": "🔁", "recurrence_days": "📆",
    }

    rows = []
    for field, icon in icons.items():
        entry = result.get(field)
        if isinstance(entry, dict):
            value     = entry.get("value")
            predicted = entry.get("predicted", False)
        else:
            value     = entry
            predicted = False
        value_str     = str(value) if value is not None else "-"
        predicted_str = "predicted" if predicted else "explicit"
        rows.append((icon, field, value_str, predicted_str))

    col_field = max(len(r[1]) for r in rows)
    col_value = max(len(r[2]) for r in rows)
    col_pred  = max(len(r[3]) for r in rows)
    inner = col_field + col_value + col_pred + 9
    lines = ["┌" + "─" * inner + "┐"]
    for icon, field, value_str, predicted_str in rows:
        lines.append(f"│  {icon}  {field:<{col_field}}  {value_str:<{col_value}}  {predicted_str:<{col_pred}}  │")
    lines.append("└" + "─" * inner + "┘")
    lines.append("  predicted = inferred by model | explicit = stated by user")
    return "\n" + "\n".join(lines)


def run_tests(predictor: TaskPlannerPredictor):
    ADD_TESTS = [
        "finish chemistry homework before Friday, pretty hard",
        "team meeting at 9am Monday, very important",
        "gym workout every Monday Thursday and Sunday, heavy session 1.5 hours",
        "read a book every evening for 30 minutes",
        "submit math assignment tonight, extremely hard, 2 hours",
        "dentist appointment at 2pm Wednesday",
        "fix the login bug before Friday, high priority, probably 4 hours",
        "meditate every morning for 15 minutes",
        "call mom this weekend",
        "buy groceries tomorrow, quick errand",
    ]

    MODIFY_TESTS = [
        ("finish chemistry homework before Friday, pretty hard",              "make it 2 hours and push deadline to Sunday"),
        ("gym workout every Monday Thursday and Sunday, heavy session 1.5 hours", "light session at home"),
        ("team meeting at 9am Monday, very important",                        "no longer fixed, just before Monday evening"),
    ]

    print("\n" + "=" * 60)
    print("ADD TESTS")
    print("=" * 60)
    for t in ADD_TESTS:
        print(f"\nINPUT: {t}")
        result = predictor.predict_add(t)
        print(format_output(result))

    print("\n" + "=" * 60)
    print("MODIFY TESTS")
    print("=" * 60)
    for add_prompt, change in MODIFY_TESTS:
        print(f"\nORIGINAL: {add_prompt}")
        base = predictor.predict_add(add_prompt)
        print(f"CHANGE:   {change}")
        changes = predictor.predict_modify(base, change)
        print("CHANGED FIELDS:")
        print(format_output(changes))


if __name__ == "__main__":
    import argparse
    arg_parser = argparse.ArgumentParser(description="VM.AI Parser")
    arg_parser.add_argument("--test",  action="store_true", help="Run test suite")
    arg_parser.add_argument("--input", type=str,            help="Single add prediction")
    args = arg_parser.parse_args()

    predictor = TaskPlannerPredictor()

    if args.test:
        run_tests(predictor)
    elif args.input:
        result = predictor.predict_add(args.input)
        print(format_output(result))
    else:
        run_tests(predictor)