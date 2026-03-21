"""
    The VM.AI Data Generator from YAML
    This class is responsible for generating training data

    Written for testing purposes but also to be used in the main training code
    Written by: Vanea @ 06-03-2026
    Updated by: Vanea @ 18-03-2026 — add/modify split, JSON schema output
    Updated by: Vanea @ 18-03-2026 — real examples mixed in from VMAI_REAL_Data.yaml
    Updated by: Vanea @ 20-03-2026 — fix start.predicted: false when DATE/TIME explicit in template
    Updated by: Vanea @ 21-03-2026 — switch target format from JSON to pipe (name=x | deadline=y)
"""

import vars
import json
import random
import argparse
from datasets import Dataset

print_sentences = False

PREDICTED_TRUE_FIELDS = {"difficulty", "duration", "category", "location", "importance"}

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

RECURRENCE_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CHANGE_TEMPLATES = [
    ("duration",   lambda v: f"make it {v} minutes",           lambda: str(random.randint(15, 180))),
    ("deadline",   lambda v: f"push deadline to {v}",          lambda: random.choice(["Sunday", "next Monday", "Friday", "tomorrow"])),
    ("location",   lambda v: f"do it at {v}",                  lambda: random.choice(["home", "office", "gym", "library", "online"])),
    ("difficulty", lambda v: f"it's a {'hard' if float(v) > 0.5 else 'light'} session", lambda: str(round(random.uniform(0.1, 0.95), 2))),
    ("importance", lambda v: f"it's {'very important' if float(v) > 0.5 else 'not urgent'}", lambda: str(round(random.uniform(0.1, 0.99), 2))),
]


def schema_to_pipe(schema: dict) -> str:
    """Convert full schema dict to flat pipe string for model target."""
    parts = []
    for field, entry in schema.items():
        val = entry["value"]
        if val is not None and val is not False:
            if isinstance(val, list):
                val = ",".join(val)
            parts.append(f"{field}={val}")
        elif val is False and field in ("fixed_time", "recurrent"):
            parts.append(f"{field}=false")
    return " | ".join(parts)


def changed_to_pipe(changed_fields: dict) -> str:
    """Convert changed fields dict to flat pipe string for modify target."""
    parts = []
    for field, entry in changed_fields.items():
        val = entry["value"]
        if val is not None:
            parts.append(f"{field}={val}")
    return " | ".join(parts)


class VMAI_DataGenerator:
    def __init__(self, training_data, real_examples=None):
        self.training_data = training_data
        self.real_examples = real_examples or []

    def generate(self, max_examples=100000):
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

        for example in self.real_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        if print_sentences:
            midpoint = len(data["input_text"]) // 2
            samples = (
                list(zip(data["input_text"][:2], data["target_text"][:2])) +
                list(zip(data["input_text"][midpoint:midpoint+2], data["target_text"][midpoint:midpoint+2]))
            )
            for i, t in samples:
                print("IN:     " + i)
                print("TARGET: " + t)
                print()

        return Dataset.from_dict(data)

    def _fill_template(self):
        templates = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()

        template = random.choice(templates)
        sentence = template
        placeholder_map = {}

        for ph, options in all_placeholders.items():
            tag = f"[{ph}]"
            if tag in sentence:
                value = str(random.choice(options))
                sentence = sentence.replace(tag, value)
                placeholder_map[ph] = value

        return sentence.lower().strip(), placeholder_map

    def _build_full_schema(self, placeholder_map):
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
            predicted = field in PREDICTED_TRUE_FIELDS
            schema[field]["value"] = value
            schema[field]["predicted"] = predicted

        if "DATE" in placeholder_map or "TIME" in placeholder_map:
            schema["start"]["predicted"] = False

        if random.random() < 0.2:
            days = random.sample(RECURRENCE_DAYS, k=random.randint(1, 3))
            schema["recurrent"]["value"] = True
            schema["recurrence_days"]["value"] = days
            schema["start"]["value"] = None
            schema["deadline"]["value"] = None

        elif random.random() < 0.2 and schema["start"]["value"]:
            schema["fixed_time"]["value"] = True
            schema["fixed_start"]["value"] = schema["start"]["value"]
            schema["start"]["value"] = None
            schema["deadline"]["value"] = None

        return schema

    def _convert_real(self, example: dict):
        sentence = example["input"]
        output   = example["output"]

        if sentence.startswith("modify:"):
            input_text  = sentence
            parts = []
            for k, v in output.items():
                if v is not None:
                    parts.append(f"{k}={v}")
            target_text = " | ".join(parts)
            return input_text, target_text

        schema = {
            "name":            {"value": output.get("name"),                    "predicted": False},
            "start":           {"value": output.get("start"),                   "predicted": False},
            "deadline":        {"value": output.get("deadline"),                "predicted": False},
            "difficulty":      {"value": output.get("difficulty"),              "predicted": True},
            "duration":        {"value": output.get("duration"),                "predicted": True},
            "category":        {"value": output.get("category"),                "predicted": True},
            "location":        {"value": output.get("location"),                "predicted": True},
            "importance":      {"value": output.get("importance"),              "predicted": True},
            "fixed_time":      {"value": output.get("fixed_time",   False),     "predicted": False},
            "fixed_start":     {"value": output.get("fixed_start"),             "predicted": False},
            "recurrent":       {"value": output.get("recurrent",    False),     "predicted": False},
            "recurrence_days": {"value": output.get("recurrence_days"),         "predicted": False},
        }

        input_text  = f"add: {sentence.lower().strip()}"
        target_text = schema_to_pipe(schema)
        return input_text, target_text

    def _generate_add(self):
        sentence, placeholder_map = self._fill_template()
        schema = self._build_full_schema(placeholder_map)
        input_text  = f"add: {sentence}"
        target_text = schema_to_pipe(schema)
        return input_text, target_text

    def _generate_modify(self):
        _, placeholder_map = self._fill_template()
        existing = self._build_full_schema(placeholder_map)

        changeable = [c for c in CHANGE_TEMPLATES if existing.get(c[0], {}).get("value") is not None
                      or c[0] in ("duration", "deadline", "location", "difficulty", "importance")]
        changes = random.sample(changeable, k=random.randint(1, min(2, len(changeable))))

        changed_fields = {}
        change_phrases = []

        for field_name, phrase_fn, value_fn in changes:
            new_value = value_fn()
            change_phrases.append(phrase_fn(new_value))
            changed_fields[field_name] = {"value": new_value, "predicted": False}

        change_prompt = ", ".join(change_phrases)

        existing_summary = {
            k: v["value"] for k, v in existing.items() if v["value"] is not None
        }

        input_text  = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} │ {change_prompt}"
        target_text = changed_to_pipe(changed_fields)
        return input_text, target_text


if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
    import os
    print_sentences = True

    parser_arg = argparse.ArgumentParser(description="VM.AI Data Generator")
    parser_arg.add_argument("--sentences", type=int, default=1000, help="Number of sentences to generate (default: 1000)")
    args = parser_arg.parse_args()

    yaml_parser = VMAI_YamlParser(f"./data/{vars.SYNTHETIC_DATASET_PATH}")
    yaml_parser.load_yaml()
    training_data = yaml_parser.parse()

    real_examples = []
    real_path = f"./data/{vars.REAL_DATASET_PATH}"
    if os.path.exists(real_path):
        real_parser = VMAI_RealDataParser(real_path)
        real_parser.load_yaml()
        real_examples = real_parser.parse()
        print(f"Real examples loaded: {len(real_examples)}")
    else:
        print("No real data file found — using synthetic only")

    print("VM.AI Sentence Generation Test:")
    print(f"Generating {args.sentences} sentences...")
    print("-" * 30)

    dataset = VMAI_DataGenerator(training_data, real_examples).generate(max_examples=args.sentences)

    print("-" * 30)
    print(f"Successfully generated {len(dataset)} examples.")