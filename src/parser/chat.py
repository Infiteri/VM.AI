"""
    VM.AI Chat Testing Interface

    Written by: Vanea @ 21-03-2026 — full rewrite, pipe format
"""

import torch
from cfg import Config
import json
import re
from transformers import AutoTokenizer, T5ForConditionalGeneration
from typing import Dict

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
    def __init__(self):
        cfg = Config()
        print("Loading model...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.output_dir)
        self.model = T5ForConditionalGeneration.from_pretrained(cfg.output_dir)
        self.model.to(self.device)
        self.model.eval()
        print(f"✓ Model ready ({self.device})")

    def _normalize(self, text: str) -> str:
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
            decoder_input = self.tokenizer("name=", return_tensors="pt", add_special_tokens=False).input_ids.to(self.device)

            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=decoder_input,
                max_new_tokens=64,
                num_beams=4,
                early_stopping=True,
            )

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

    def _pipe_to_schema(self, flat: str) -> Dict:
        raw = {}
        for part in flat.split("|"):
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
            schema[field] = {"value": val, "predicted": field in PREDICTED_FIELDS}
        return schema

    def _pipe_to_changed(self, flat: str) -> Dict:
        changed = {}
        for part in flat.split("|"):
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
        return changed

    def predict_add(self, sentence: str) -> Dict:
        output = self._run_model(f"add: {self._normalize(sentence)}")
        if "=" not in output:
            return {"error": "parse_failed", "raw": output}
        result = self._pipe_to_schema(output)
        if not result.get("name", {}).get("value"):
            return {"error": "parse_failed", "raw": output}
        return result

    def predict_modify(self, existing_task: Dict, change_prompt: str) -> Dict:
        summary = {
            k: v["value"] if isinstance(v, dict) else v
            for k, v in existing_task.items()
            if (v["value"] if isinstance(v, dict) else v) is not None
        }
        input_text = f"modify: {json.dumps(summary, ensure_ascii=False)} \u2502 {self._normalize(change_prompt)}"
        output = self._run_model(input_text)
        changed = self._pipe_to_changed(output)
        if not changed:
            return {"error": "parse_failed", "raw": output}
        return changed


def format_output(result: Dict) -> str:
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


def main():
    print("\n" + "=" * 60)
    print("🗓️  VM.AI TASK PLANNER CHAT")
    print("=" * 60)
    print("  add: <prompt>    — extract a new task")
    print("  modify           — modify last add result")
    print("  modify json      — paste your own JSON to modify")
    print("  end              — exit")
    print("=" * 60)

    predictor   = TaskPlannerPredictor()
    count       = 0
    last_result = None

    while True:
        user_input = input(f"\n{count+1:2d} > ").strip()
        if not user_input:
            continue

        if user_input.lower() == "end":
            print(f"\nProcessed {count} inputs")
            break

        try:
            if user_input.lower().startswith("add:"):
                sentence    = user_input[4:].strip()
                last_result = predictor.predict_add(sentence)
                print(format_output(last_result))
                count += 1

            elif user_input.lower() == "modify json":
                raw = input("   Paste task JSON > ").strip()
                if not raw:
                    continue
                try:
                    pasted = json.loads(raw)
                except json.JSONDecodeError:
                    print("   ⚠️  Invalid JSON")
                    continue
                change  = input("   What to change? > ").strip()
                if not change:
                    continue
                changes = predictor.predict_modify(pasted, change)
                print("\n   Changed fields:")
                print(format_output(changes))
                last_result = pasted
                for field, entry in changes.items():
                    if isinstance(entry, dict):
                        last_result[field] = entry
                count += 1

            elif user_input.lower() == "modify":
                if last_result is None or "error" in last_result:
                    print("   ⚠️  No valid task to modify. Run add: first.")
                    continue
                change  = input("   What to change? > ").strip()
                if not change:
                    continue
                changes = predictor.predict_modify(last_result, change)
                print("\n   Changed fields:")
                print(format_output(changes))
                for field, entry in changes.items():
                    if field in last_result and isinstance(last_result[field], dict):
                        last_result[field] = entry
                count += 1

            else:
                print("   ⚠️  Start with 'add:' or type 'modify'. Type 'end' to exit.")

        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    main()