"""
    The VM.AI chat testing interface
"""

import torch
import json
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
                max_new_tokens=256
            )

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

    def _parse_output(self, output_text: str) -> Dict:
        # Try new JSON format first
        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            pass

        # Fallback: old pipe format — TASK: x | DEADLINE: y
        old_key_map = {
            "TASK":       "name",
            "DEADLINE":   "deadline",
            "DATE":       "start",
            "TIME":       "start",
            "DURATION":   "duration",
            "LOCATION":   "location",
            "PRIORITY":   "importance",
            "DIFFICULTY": "difficulty",
            "CATEGORY":   "category",
        }
        predicted_true = {"difficulty", "duration", "category", "location", "importance"}

        result = {}
        for part in output_text.split("|"):
            part = part.strip()
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            key   = key.strip().upper()
            value = value.strip()
            field = old_key_map.get(key)
            if field and value:
                result[field] = {
                    "value":     value,
                    "predicted": field in predicted_true
                }

        if not result:
            return {"error": "parse_failed", "raw": output_text}

        return result

    def predict_add(self, sentence: str) -> Dict:
        input_text = f"add: {self.normalize(sentence)}"
        output_text = self._run_model(input_text)
        return self._parse_output(output_text)

    def predict_modify(self, existing_task: Dict, change_prompt: str) -> Dict:
        existing_summary = {
            k: v["value"] if isinstance(v, dict) else v
            for k, v in existing_task.items()
            if (v["value"] if isinstance(v, dict) else v) is not None
        }
        input_text = f"modify: {json.dumps(existing_summary)} │ {self.normalize(change_prompt)}"
        output_text = self._run_model(input_text)

        return self._parse_output(output_text)


def format_output(result: Dict):
    if "error" in result:
        return f"   ❌ Model output could not be parsed\n   raw: {result['raw']}"

    if not result:
        return "   ❌ Nothing extracted"

    icons = {
        "name":            "📋",
        "start":           "🕐",
        "deadline":        "📅",
        "difficulty":      "💪",
        "duration":        "⏱️",
        "category":        "🏷️",
        "location":        "📍",
        "importance":      "⚡",
        "fixed_time":      "📌",
        "fixed_start":     "🔒",
        "recurrent":       "🔁",
        "recurrence_days": "📆",
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
    lines = []
    lines.append("┌" + "─" * inner + "┐")
    for icon, field, value_str, predicted_str in rows:
        lines.append(f"│  {icon}  {field:<{col_field}}  {value_str:<{col_value}}  {predicted_str:<{col_pred}}  │")
    lines.append("└" + "─" * inner + "┘")
    lines.append("  predicted = inferred by model | explicit = stated by user")

    return "\n" + "\n".join(lines)


def main():
    print("\n" + "=" * 60)
    print("🗓️  VM.AI TASK PLANNER CHAT")
    print("=" * 60)
    print("Commands:")
    print("  add: <prompt>             — extract a new task")
    print("  modify                    — modify last add result")
    print("  modify json               — paste your own JSON to modify")
    print("  end                       — exit")
    print("=" * 60)

    predictor = TaskPlannerPredictor()
    count = 0
    last_result = None

    while True:
        user_input = input(f"\n{count+1:2d} > ").strip()

        if not user_input:
            continue

        if user_input.lower() == "end":
            print(f"\nProcessed {count} sentences")
            break

        try:
            if user_input.lower().startswith("add:"):
                sentence = user_input[4:].strip()
                last_result = predictor.predict_add(sentence)
                print(format_output(last_result))
                count += 1

            elif user_input.lower() == "modify json":
                raw = input("   Paste task JSON > ").strip()
                if not raw:
                    continue
                try:
                    pasted_task = json.loads(raw)
                except json.JSONDecodeError:
                    print("   ⚠️  Invalid JSON — check your input and try again.")
                    continue
                change = input("   What to change? > ").strip()
                if not change:
                    continue
                changes = predictor.predict_modify(pasted_task, change)
                print("\n   Changed fields:")
                print(format_output(changes))

                last_result = pasted_task
                for field, entry in changes.items():
                    if isinstance(entry, dict):
                        last_result[field] = entry
                count += 1

            elif user_input.lower() == "modify":
                if last_result is None or "error" in last_result:
                    print("   ⚠️  No valid task to modify. Run an add: first.")
                    continue
                change = input("   What to change? > ").strip()
                if not change:
                    continue
                changes = predictor.predict_modify(last_result, change)
                print("\n   Changed fields:")
                print(format_output(changes))

                # Merge changes back into last_result
                for field, entry in changes.items():
                    if field in last_result and isinstance(last_result[field], dict):
                        last_result[field] = entry
                count += 1

            else:
                print("   ⚠️  Start with 'add:' or type 'modify'. Type 'end' to exit.")

        except Exception as e:
            print(f"   Prediction error: {e}")


if __name__ == "__main__":
    main()