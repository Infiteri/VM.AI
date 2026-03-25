"""
    VM.AI Data Generator
    Generates training data in pipe format: name=x | deadline=y | difficulty=0.75

    Written by: Vanea @ 06-03-2026
    Updated by: Vanea @ 21-03-2026 — full rewrite, pipe format output
    Updated by: Vanea @ 21-03-2026 — keyword-driven recurrent/fixed_time, no random guessing
"""

import vars
import json
import random
import argparse
import re
from datasets import Dataset

PREDICTED_FIELDS = {"difficulty", "duration", "category", "location", "importance", "start"}
FIELD_MAP = {
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

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_LOWER = {d.lower(): d for d in DAYS}

RECURRENT_KEYWORDS = ["every", "daily", "each", "weekday", "weekly"]

CHANGE_TEMPLATES = [
    ("duration",   lambda v: f"make it {v} minutes",                                         lambda: str(random.randint(15, 180))),
    ("deadline",   lambda v: f"push deadline to {v}",                                        lambda: random.choice(["Sunday", "next Monday", "Friday", "tomorrow"])),
    ("location",   lambda v: f"do it at {v}",                                                lambda: random.choice(["home", "office", "gym", "library", "online"])),
    ("difficulty", lambda v: f"it's a {'hard' if float(v) > 0.5 else 'light'} session",     lambda: str(round(random.uniform(0.1, 0.95), 2))),
    ("importance", lambda v: f"it's {'very important' if float(v) > 0.5 else 'not urgent'}", lambda: str(round(random.uniform(0.1, 0.99), 2))),
]


def schema_to_pipe(schema: dict) -> str:
    parts = []
    for field, entry in schema.items():
        val = entry["value"]
        if isinstance(val, bool):
            parts.append(f"{field}={'true' if val else 'false'}")
        elif isinstance(val, list):
            parts.append(f"{field}={','.join(val)}")
        elif val is not None:
            parts.append(f"{field}={val}")
    return " | ".join(parts)


def changed_to_pipe(changed: dict) -> str:
    parts = []
    for field, entry in changed.items():
        val = entry["value"]
        if val is not None:
            parts.append(f"{field}={val}")
    return " | ".join(parts)


class DataGenerator:
    def __init__(self, training_data, real_examples=None, specific_examples=None):
        self.training_data     = training_data
        self.real_examples     = real_examples or []
        self.specific_examples = specific_examples or []

    def generate(self, max_examples=10000):
        half = max_examples // 2
        data = {"input_text": [], "target_text": []}

        for _ in range(half):
            inp, tgt = self._generate_add()
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        for _ in range(half):
            inp, tgt = self._generate_modify()
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        # real examples included twice for extra weight
        for example in self.real_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        for example in self.real_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        for example in self.specific_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        return Dataset.from_dict(data)

    def _fill_template(self):
        templates        = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()
        template         = random.choice(templates)
        sentence         = template
        placeholder_map  = {}
        for ph, options in all_placeholders.items():
            tag = f"[{ph}]"
            while tag in sentence:
                value = str(random.choice(options))
                sentence = sentence.replace(tag, value)
                placeholder_map[ph] = value
        return sentence.lower().strip(), placeholder_map

    def _build_schema(self, placeholder_map, sentence=""):
        schema = {
            "name":            {"value": None,  "predicted": False},
            "start":           {"value": None,  "predicted": True},
            "deadline":        {"value": None,  "predicted": False},
            "difficulty":      {"value": None,  "predicted": True},
            "duration":        {"value": None,  "predicted": True},
            "category":        {"value": None,  "predicted": True},
            "location":        {"value": None,  "predicted": True},
            "importance":      {"value": None,  "predicted": True},
            "fixed_time":      {"value": False, "predicted": False},
            "fixed_start":     {"value": None,  "predicted": False},
            "recurrent":       {"value": False, "predicted": False},
            "recurrence_days": {"value": None,  "predicted": False},
        }

        for yaml_key, value in placeholder_map.items():
            field = FIELD_MAP.get(yaml_key)
            if not field:
                continue
            schema[field]["value"]     = value
            schema[field]["predicted"] = field in PREDICTED_FIELDS

        s = sentence.lower()
        
        # Check for explicit time (FIXED)
        has_explicit_time = (
            "at" in s or 
            "sharp" in s or
            re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', s) is not None or
            "morning" in s or 
            "afternoon" in s or 
            "evening" in s or 
            "noon" in s
        )
        
        has_recurrent = any(kw in s for kw in RECURRENT_KEYWORDS)
        
        # Handle recurrence first (overrides fixed_time)
        if has_recurrent:
            schema["recurrent"]["value"] = True
            schema["start"]["value"]     = None
            schema["deadline"]["value"]  = None
            schema["fixed_time"]["value"] = False
            schema["fixed_start"]["value"] = None

            if "every day" in s or "daily" in s:
                schema["recurrence_days"]["value"] = DAYS.copy()
            elif "weekday" in s:
                schema["recurrence_days"]["value"] = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
            else:
                mentioned = [DAYS_LOWER[d] for d in DAYS_LOWER if d in s]
                schema["recurrence_days"]["value"] = mentioned if mentioned else random.sample(DAYS, k=random.randint(1, 3))
        
        # Handle fixed time (only if explicitly mentioned)
        elif has_explicit_time:
            schema["fixed_time"]["value"] = True
            schema["start"]["value"] = None
            schema["deadline"]["value"] = None
            
            # Extract time from sentence
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))|(morning|afternoon|evening|noon)', s)
            if time_match:
                time_str = time_match.group(0)
                # Normalize time
                if "morning" in time_str:
                    schema["fixed_start"]["value"] = "08:00"
                elif "afternoon" in time_str:
                    schema["fixed_start"]["value"] = "13:00"
                elif "evening" in time_str:
                    schema["fixed_start"]["value"] = "18:00"
                elif "noon" in time_str:
                    schema["fixed_start"]["value"] = "12:00"
                else:
                    schema["fixed_start"]["value"] = time_str
        
        # Handle "today" as start (not fixed_time)
        if "today" in s and not has_recurrent and not has_explicit_time:
            if schema["start"]["value"] is None:
                schema["start"]["value"] = "today"
                schema["start"]["predicted"] = False

        return schema

    def _convert_real(self, example: dict):
        sentence = example["input"]
        output   = example["output"]

        if sentence.startswith("modify:"):
            parts = []
            for k, v in output.items():
                if v is not None:
                    parts.append(f"{k}={v}")
            return sentence, " | ".join(parts)

        schema = {
            "name":            {"value": output.get("name"),               "predicted": False},
            "start":           {"value": output.get("start"),              "predicted": False},
            "deadline":        {"value": output.get("deadline"),           "predicted": False},
            "difficulty":      {"value": output.get("difficulty"),         "predicted": True},
            "duration":        {"value": output.get("duration"),           "predicted": True},
            "category":        {"value": output.get("category"),           "predicted": True},
            "location":        {"value": output.get("location"),           "predicted": True},
            "importance":      {"value": output.get("importance"),         "predicted": True},
            "fixed_time":      {"value": output.get("fixed_time",  False), "predicted": False},
            "fixed_start":     {"value": output.get("fixed_start"),        "predicted": False},
            "recurrent":       {"value": output.get("recurrent",   False), "predicted": False},
            "recurrence_days": {"value": output.get("recurrence_days"),    "predicted": False},
        }

        return f"add: {sentence.lower().strip()}", schema_to_pipe(schema)

    def _generate_add(self):
        sentence, placeholder_map = self._fill_template()
        schema = self._build_schema(placeholder_map, sentence)
        
        # Additional validation to ensure consistent outputs
        s = sentence.lower()
        
        # Double-check: if no explicit time, fixed_time should be false
        has_explicit_time = (
            "at" in s or 
            "sharp" in s or
            re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', s) is not None or
            "morning" in s or 
            "afternoon" in s or 
            "evening" in s or 
            "noon" in s
        )
        
        if not has_explicit_time and schema["fixed_time"]["value"] == True:
            schema["fixed_time"]["value"] = False
            schema["fixed_start"]["value"] = None
        
        return f"add: {sentence}", schema_to_pipe(schema)

    def _generate_modify(self):
        sentence, placeholder_map = self._fill_template()
        existing = self._build_schema(placeholder_map, sentence)

        changes        = random.sample(CHANGE_TEMPLATES, k=random.randint(1, 2))
        changed_fields = {}
        change_phrases = []

        for field_name, phrase_fn, value_fn in changes:
            new_value = value_fn()
            change_phrases.append(phrase_fn(new_value))
            changed_fields[field_name] = {"value": new_value, "predicted": False}

        existing_summary = {
            k: v["value"] for k, v in existing.items() if v["value"] is not None
        }

        input_text  = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} \u2502 {', '.join(change_phrases)}"
        target_text = changed_to_pipe(changed_fields)
        return input_text, target_text


if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
    import os

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--sentences", type=int, default=10)
    args = arg_parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")

    yp = VMAI_YamlParser(os.path.join(cfg_path, vars.SYNTHETIC_DATASET))
    yp.load_yaml()
    training_data = yp.parse()

    rp = VMAI_RealDataParser(os.path.join(cfg_path, vars.REAL_DATASET))
    rp.load_yaml()
    real_data = rp.parse()  

    ds = DataGenerator(training_data, real_data).generate(args.sentences)  
    
    for i in range(min(100, len(ds))):
        print("IN: ", ds["input_text"][i])
        print("OUT:", ds["target_text"][i])
        print()