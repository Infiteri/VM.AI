"""
    The VM.AI Data Generator from YAML
    This class is responsible for generating training data

    Written for testing purposes but also to be used in the main training code
    Written by: Vanea @ 06-03-2026
    Updated by: Vanea @ 18-03-2026 — add/modify split, JSON schema output
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


class VMAI_DataGenerator:
    def __init__(self, training_data):
        self.training_data = training_data

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

        if print_sentences:
            for i, t in zip(data["input_text"][:4], data["target_text"][:4]):
                print("IN:     " + i)
                print("TARGET: " + t)
                print()

        return Dataset.from_dict(data)

    def _fill_template(self):
        """Pick a random template, fill placeholders, return (sentence, placeholder_map)."""
        templates = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()

        template = random.choice(templates)
        sentence = template
        placeholder_map = {}  # {yaml_key: filled_value}

        for ph, options in all_placeholders.items():
            tag = f"[{ph}]"
            if tag in sentence:
                value = str(random.choice(options))
                sentence = sentence.replace(tag, value)
                placeholder_map[ph] = value

        return sentence.lower().strip(), placeholder_map

    def _build_full_schema(self, placeholder_map):
        """Build the full output JSON schema from a placeholder_map."""
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

    def _generate_add(self):
        sentence, placeholder_map = self._fill_template()
        schema = self._build_full_schema(placeholder_map)
        input_text = f"add: {sentence}"
        target_text = json.dumps(schema, ensure_ascii=False)
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

        input_text = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} | {change_prompt}"
        target_text = json.dumps(changed_fields, ensure_ascii=False)
        return input_text, target_text


if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser
    print_sentences = True

    parser_arg = argparse.ArgumentParser(description="VM.AI Data Generator")
    parser_arg.add_argument("--sentences", type=int, default=1000, help="Number of sentences to generate (default: 1000)")
    args = parser_arg.parse_args()

    yaml_parser = VMAI_YamlParser(f"./data/{vars.SYNTHETIC_DATASET_PATH}")
    yaml_parser.load_yaml()
    training_data = yaml_parser.parse()

    print("VM.AI Sentence Generation Test:")
    print(f"Generating {args.sentences} sentences...")
    print("-" * 30)

    dataset = VMAI_DataGenerator(training_data).generate(max_examples=args.sentences)

    print("-" * 30)
    print(f"Successfully generated {len(dataset)} examples.")