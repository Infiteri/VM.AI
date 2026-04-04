"""
    VM.AI Chat Testing Interface

    Written by: Vanea @ 21-03-2026 — full rewrite, pipe format
"""

import torch
from cfg import Config
import json
import re
import os
import yaml
from datetime import datetime
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

LOG_FILE = "performance_log.yaml"


def log_entry(mode: str, sentence: str, raw_output: str, parsed_result: Dict):
    """Append one test entry to the performance log."""
    entry = {
        "timestamp":  datetime.now().isoformat(),
        "mode":       mode,
        "input":      sentence,
        "raw_output": raw_output,
        "parsed":     {
            k: (v["value"] if isinstance(v, dict) else v)
            for k, v in parsed_result.items()
        } if "error" not in parsed_result else None,
        "error":      parsed_result.get("error"),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        yaml.dump([entry], f, allow_unicode=True, sort_keys=False)
        f.write("\n")


class TaskPlannerPredictor:
    def __init__(self):
        cfg = Config()
        print("Loading model...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(cfg.output_dir)
        self.model = T5ForConditionalGeneration.from_pretrained(cfg.output_dir)
        self.model.to(self.device)
        self.model.eval()
        self._last_raw_output = ""
        print(f"✓ Model ready ({self.device})")

    # Regex that matches an explicit clock time in the raw sentence
    _TIME_RE = re.compile(
        r'\b(\d{1,2}:\d{2}|\d{1,2}\s*[ap]m|@\s*\d{1,2})\b', re.IGNORECASE
    )

    def _normalize(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r'(\d)(am|pm)', r'\1 \2', text)
        return text

    @staticmethod
    def _normalize_time(time_str: str) -> str | None:
        """Convert various time formats to HH:MM."""
        if not time_str:
            return None
        time_str = time_str.strip().lower()

        # Handle "6am", "6 am", "6:30pm" format
        match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"

        # Handle "morning", "afternoon", "evening", "noon"
        if "morning" in time_str:
            return "08:00"
        if "afternoon" in time_str:
            return "13:00"
        if "evening" in time_str:
            return "18:00"
        if "noon" in time_str:
            return "12:00"
        if "midnight" in time_str:
            return "00:00"

        # Already HH:MM
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            return time_str

        return None

    def _sanity_check(self, schema: Dict, original_sentence: str) -> Dict:
        """
        Post-generation guard:
        - fixed_time should only be True if the input sentence contains an
          explicit clock time (HH:MM, Xam/pm, @Xpm).  If the model hallucinated
          it, reset to False and clear fixed_start.
        - fixed_start values are normalized to HH:MM format.
        """
        # ── fix fixed_time hallucination ────────────────────────────────────
        ft = schema.get("fixed_time", {})
        ft_val = ft.get("value") if isinstance(ft, dict) else ft
        if ft_val is True:
            if not self._TIME_RE.search(original_sentence):
                schema["fixed_time"]["value"] = False
                schema["fixed_start"]["value"] = None

        # ── normalize and validate fixed_start ──────────────────────────────
        fs = schema.get("fixed_start", {})
        fs_val = fs.get("value") if isinstance(fs, dict) else fs
        if fs_val is not None:
            normalized = self._normalize_time(str(fs_val))
            if normalized:
                schema["fixed_start"]["value"] = normalized
            else:
                schema["fixed_start"]["value"] = None

        return schema

    def _run_model(self, input_text: str) -> str:
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            padding=True,
        ).to(self.device)

        decoder_input = self.tokenizer(
            "name=",
            return_tensors="pt",
            add_special_tokens=False
        ).input_ids.to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                decoder_input_ids=decoder_input,
                max_new_tokens=256,
                no_repeat_ngram_size=4,
                repetition_penalty=1.5,
            )

        raw = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        self._last_raw_output = raw
        return raw

    def _pipe_to_schema(self, flat: str) -> Dict:
        raw = {}
        for part in flat.split("|"):
            part = part.strip()
            if "=" not in part:
                continue
            k, _, v = part.partition("=")
            k, v = k.strip(), v.strip()
            if v.lower() == "null":
                v = None
            elif v.lower() in ("true", "tru", "t"):
                v = True
            elif v.lower().startswith("fals"):
                v = False
            if k not in raw:
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
            if v.lower() == "null":
                v = None
            elif v.lower() in ("true", "tru", "t"):
                v = True
            elif v.lower().startswith("fals"):
                v = False
            if k and k not in changed:
                changed[k] = {"value": v, "predicted": False}
        return changed

    def predict_add(self, sentence: str) -> Dict:
        output = self._run_model(f"add: {self._normalize(sentence)}")
        if "=" not in output:
            result = {"error": "parse_failed", "raw": output}
        else:
            result = self._pipe_to_schema(output)
            if not result.get("name", {}).get("value"):
                result = {"error": "parse_failed", "raw": output}
            else:
                result = self._sanity_check(result, sentence)
        log_entry("add", sentence, self._last_raw_output, result)
        return result

    def predict_modify(self, existing_task: Dict, change_prompt: str) -> Dict:
        summary = {}
        for k, v in existing_task.items():
            val = v["value"] if isinstance(v, dict) else v
            if val is not None:
                # Convert booleans for JSON
                if isinstance(val, bool):
                    val = "true" if val else "false"
                summary[k] = val
        input_text = f"modify: {json.dumps(summary, ensure_ascii=False)} \u2502 {self._normalize(change_prompt)}"
        output = self._run_model(input_text)

        # Model outputs FULL task in pipe format, parse it
        new_task = self._pipe_to_schema(output)
        if "error" in new_task:
            result = {"error": "parse_failed", "raw": output}
            log_entry("modify", change_prompt, self._last_raw_output, result)
            return result

        # Diff old vs new → return only changed fields
        changed = self._diff_schemas(existing_task, new_task)
        if not changed:
            result = {"error": "no_changes", "raw": output}
        else:
            result = changed
        log_entry("modify", change_prompt, self._last_raw_output, result)
        return result

    @staticmethod
    def _diff_schemas(old_task: Dict, new_task: Dict) -> Dict:
        """Compare old and new task schemas, return only changed fields."""
        changed = {}
        for field, new_entry in new_task.items():
            new_val = new_entry.get("value") if isinstance(new_entry, dict) else new_entry
            old_entry = old_task.get(field)
            old_val = old_entry.get("value") if isinstance(old_entry, dict) else old_entry

            # Normalize for comparison
            if isinstance(old_val, bool):
                old_val = old_val
            elif isinstance(new_val, bool):
                new_val = new_val
            else:
                # String comparison
                old_val = str(old_val).lower() if old_val is not None else None
                new_val = str(new_val).lower() if new_val is not None else None

            if old_val != new_val:
                changed[field] = {"value": new_val, "predicted": new_entry.get("predicted", False) if isinstance(new_entry, dict) else False}

        return changed


def format_output(result: Dict) -> str:
    if "error" in result:
        return f"   parse failed\n   raw: {result['raw']}"
    if not result:
        return "   nothing extracted"

    fields = ["name", "start", "deadline", "difficulty", "duration",
              "category", "location", "importance", "fixed_time",
              "fixed_start", "recurrent", "recurrence_days"]

    rows = []
    for field in fields:
        entry = result.get(field)
        if isinstance(entry, dict):
            value     = entry.get("value")
            predicted = entry.get("predicted", False)
        else:
            value     = entry
            predicted = False
        value_str     = str(value).lower() if isinstance(value, bool) else (str(value) if value is not None else "-")
        predicted_str = "predicted" if predicted else "explicit"
        rows.append((field, value_str, predicted_str))

    col_field = max(len(r[0]) for r in rows)
    col_value = max(len(r[1]) for r in rows)
    col_pred  = max(len(r[2]) for r in rows)
    inner = col_field + col_value + col_pred + 6
    lines = ["┌" + "─" * inner + "┐"]
    for field, value_str, predicted_str in rows:
        lines.append(f"│  {field:<{col_field}}  {value_str:<{col_value}}  {predicted_str:<{col_pred}}  │")
    lines.append("└" + "─" * inner + "┘")
    lines.append("  predicted = inferred by model | explicit = stated by user")
    return "\n" + "\n".join(lines)


def main():
    print("\n" + "=" * 60)
    print("   VM.AI TASK PLANNER CHAT")
    print("=" * 60)
    print("  add: <prompt>          — extract a new task")
    print("  modify                 — modify last add result")
    print("  modify json            — paste JSON then type change")
    print("  modify: {..} │ <change> — paste full modify string")
    print("  end                    — exit")
    print("=" * 60)
    print(f"  Logging to: {os.path.abspath(LOG_FILE)}")
    print("=" * 60)

    predictor   = TaskPlannerPredictor()
    count       = 0
    last_result = None

    while True:
        user_input = input(f"\n{count+1:2d} > ").strip()
        if not user_input:
            continue

        if user_input.lower() == "end":
            print(f"\nProcessed {count} inputs — log saved to {os.path.abspath(LOG_FILE)}")
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
                    print("   Invalid JSON")
                    continue
                change = input("   What to change? > ").strip()
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

            elif user_input.lower().startswith("modify:"):
                # inline: modify: {...} │ change prompt
                rest = user_input[7:].strip()
                if "│" not in rest:
                    print("   Missing │ separator.")
                    continue
                json_part, _, change_part = rest.partition("│")
                try:
                    pasted = json.loads(json_part.strip())
                except json.JSONDecodeError:
                    print("   Invalid JSON in modify string.")
                    continue
                change = change_part.strip()
                if not change:
                    print("   Missing change prompt after │.")
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
                    print("   No valid task to modify. Run add: first.")
                    continue
                change = input("   What to change? > ").strip()
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
                print("   Start with 'add:' or 'modify:'. Type 'end' to exit.")

        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    main()