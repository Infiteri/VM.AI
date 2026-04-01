"""
    VM.AI Data Generator
    Generates training data in pipe format: name=x | deadline=y | difficulty=0.75

    Written by: Vanea @ 06-03-2026
    Updated by: Vanea @ 21-03-2026 — full rewrite, pipe format output
    Updated by: Vanea @ 21-03-2026 — keyword-driven recurrent/fixed_time, no random guessing
    Updated by: Vanea @ 01-04-2026 — expanded CHANGE_TEMPLATES (all fields), generate_modify_only()
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

# ── value generators ──────────────────────────────────────────────────────────

def _rand_duration():
    return str(random.choice([10, 15, 20, 25, 30, 45, 60, 90, 120, 150, 180]))

def _rand_deadline():
    return random.choice([
        "Sunday", "next Monday", "Friday", "tomorrow", "tonight",
        "end of day", "end of week", "next week", "this weekend",
        "Wednesday", "Thursday", "next Friday", "in 2 days", "in 3 days",
    ])

def _rand_location():
    return random.choice([
        "home", "office", "gym", "library", "online",
        "school", "the coffee shop", "the park", "remotely", "university",
    ])

def _rand_difficulty():
    return str(round(random.uniform(0.1, 0.95), 2))

def _rand_importance():
    return str(round(random.uniform(0.1, 0.99), 2))

def _rand_category():
    return random.choice([
        "work", "study", "fitness", "health", "personal",
        "finance", "home", "family", "social", "errands",
        "travel", "creative", "learning", "admin", "shopping",
    ])

def _rand_name():
    return random.choice([
        "finish the report", "review the document", "send the email",
        "prepare the presentation", "call the client", "fix the bug",
        "write the summary", "update the spreadsheet", "run the tests",
        "book the appointment", "draft the proposal", "pay the bill",
        "go for a run", "cook dinner", "study for the exam",
    ])

def _rand_time():
    return random.choice([
        "08:00", "09:00", "10:00", "11:00", "12:00",
        "13:00", "14:00", "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00",
    ])

def _rand_recurrence_days():
    count = random.randint(1, 3)
    return ",".join(random.sample(DAYS, k=count))


# ── CHANGE_TEMPLATES ──────────────────────────────────────────────────────────
# Each entry: (field_name, phrase_fn(value)->str, value_fn()->str)
# Multiple phrase variants per field are listed as separate tuples so they get
# sampled uniformly — the field just appears more than once in the list.

CHANGE_TEMPLATES = [

    # ── duration ──────────────────────────────────────────────────────────────
    ("duration", lambda v: f"make it {v} minutes",                      _rand_duration),
    ("duration", lambda v: f"change duration to {v} minutes",           _rand_duration),
    ("duration", lambda v: f"it should take {v} minutes",               _rand_duration),
    ("duration", lambda v: f"set the duration to {v} minutes",          _rand_duration),
    ("duration", lambda v: f"block {v} minutes for this",               _rand_duration),
    ("duration", lambda v: f"give it {v} minutes",                      _rand_duration),
    ("duration", lambda v: f"it'll only take {v} minutes",              _rand_duration),

    # ── deadline ──────────────────────────────────────────────────────────────
    ("deadline", lambda v: f"push deadline to {v}",                     _rand_deadline),
    ("deadline", lambda v: f"move the deadline to {v}",                 _rand_deadline),
    ("deadline", lambda v: f"it's due {v} now",                        _rand_deadline),
    ("deadline", lambda v: f"change the due date to {v}",              _rand_deadline),
    ("deadline", lambda v: f"needs to be done by {v}",                 _rand_deadline),
    ("deadline", lambda v: f"deadline is {v}",                         _rand_deadline),
    ("deadline", lambda v: f"extend the deadline to {v}",              _rand_deadline),

    # ── location ──────────────────────────────────────────────────────────────
    ("location", lambda v: f"do it at {v}",                             _rand_location),
    ("location", lambda v: f"change location to {v}",                   _rand_location),
    ("location", lambda v: f"it'll be at {v}",                         _rand_location),
    ("location", lambda v: f"move it to {v}",                          _rand_location),
    ("location", lambda v: f"it's happening at {v}",                   _rand_location),
    ("location", lambda v: f"do this from {v}",                        _rand_location),

    # ── difficulty ────────────────────────────────────────────────────────────
    ("difficulty", lambda v: f"it's a {'hard' if float(v) > 0.5 else 'light'} session",     _rand_difficulty),
    ("difficulty", lambda v: f"this is {'very difficult' if float(v) > 0.7 else 'pretty easy'}",  _rand_difficulty),
    ("difficulty", lambda v: f"mark it as {'hard' if float(v) > 0.5 else 'easy'}",          _rand_difficulty),
    ("difficulty", lambda v: f"difficulty is {'high' if float(v) > 0.6 else 'low'}",        _rand_difficulty),
    ("difficulty", lambda v: f"it's going to be {'tough' if float(v) > 0.6 else 'simple'}", _rand_difficulty),

    # ── importance ────────────────────────────────────────────────────────────
    ("importance", lambda v: f"it's {'very important' if float(v) > 0.5 else 'not urgent'}",        _rand_importance),
    ("importance", lambda v: f"mark it as {'high priority' if float(v) > 0.5 else 'low priority'}", _rand_importance),
    ("importance", lambda v: f"this is {'critical' if float(v) > 0.7 else 'optional'}",             _rand_importance),
    ("importance", lambda v: f"set priority to {'high' if float(v) > 0.5 else 'low'}",              _rand_importance),
    ("importance", lambda v: f"it's {'urgent' if float(v) > 0.6 else 'not a priority'}",            _rand_importance),

    # ── category ──────────────────────────────────────────────────────────────
    ("category", lambda v: f"categorize it as {v}",                    _rand_category),
    ("category", lambda v: f"it's a {v} task",                         _rand_category),
    ("category", lambda v: f"put it under {v}",                        _rand_category),
    ("category", lambda v: f"move it to {v}",                          _rand_category),
    ("category", lambda v: f"change category to {v}",                  _rand_category),
    ("category", lambda v: f"this belongs in {v}",                     _rand_category),

    # ── name ──────────────────────────────────────────────────────────────────
    ("name", lambda v: f"rename it to {v}",                            _rand_name),
    ("name", lambda v: f"change the name to {v}",                      _rand_name),
    ("name", lambda v: f"call it {v} instead",                         _rand_name),
    ("name", lambda v: f"the task is actually {v}",                    _rand_name),

    # ── fixed_time / fixed_start ──────────────────────────────────────────────
    # These always come as a pair — we handle them together via a special sentinel
    ("fixed_time+fixed_start", lambda v: f"set it for {v}",            _rand_time),
    ("fixed_time+fixed_start", lambda v: f"schedule it at {v}",        _rand_time),
    ("fixed_time+fixed_start", lambda v: f"it starts at {v}",          _rand_time),
    ("fixed_time+fixed_start", lambda v: f"pin it to {v}",             _rand_time),
    ("fixed_time+fixed_start", lambda v: f"lock it in at {v}",         _rand_time),
    ("fixed_time+fixed_start", lambda v: f"the time is {v}",           _rand_time),

    # ── recurrent / recurrence_days ───────────────────────────────────────────
    # Same paired approach
    ("recurrent+recurrence_days", lambda v: f"make it repeat every {v}",             _rand_recurrence_days),
    ("recurrent+recurrence_days", lambda v: f"schedule it every {v}",                _rand_recurrence_days),
    ("recurrent+recurrence_days", lambda v: f"it should happen each {v}",            _rand_recurrence_days),
    ("recurrent+recurrence_days", lambda v: f"set it as recurring on {v}",           _rand_recurrence_days),
    ("recurrent+recurrence_days", lambda v: f"repeat this on {v}",                   _rand_recurrence_days),
    ("recurrent+recurrence_days", lambda v: f"it recurs on {v}",                     _rand_recurrence_days),
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
        if isinstance(val, bool):
            parts.append(f"{field}={'true' if val else 'false'}")
        elif val is not None:
            parts.append(f"{field}={val}")
    return " | ".join(parts)


class DataGenerator:
    def __init__(self, training_data, real_examples=None, specific_examples=None):
        self.training_data     = training_data
        self.real_examples     = real_examples or []
        self.specific_examples = specific_examples or []

    # ── public generate methods ───────────────────────────────────────────────

    def generate(self, max_examples=10000):
        """Standard mixed add+modify generation (original behaviour)."""
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

    def generate_modify_only(self, max_examples=5000):
        """
        Generate a modify-only dataset for targeted fine-tuning.
        Produces purely modify: examples — no add: examples at all.
        Real modify examples (if any exist in real/specific data) are
        included with 3× repetition for extra weight.
        """
        data = {"input_text": [], "target_text": []}

        for _ in range(max_examples):
            inp, tgt = self._generate_modify()
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        # Pull real modify examples from labeled data (3× weight)
        for example in self.real_examples + self.specific_examples:
            if not isinstance(example.get("input"), str):
                continue
            if example["input"].startswith("modify:"):
                inp, tgt = self._convert_real(example)
                for _ in range(3):
                    data["input_text"].append(inp)
                    data["target_text"].append(tgt)

        return Dataset.from_dict(data)

    # ── internal helpers ──────────────────────────────────────────────────────

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

    def _has_explicit_time(self, sentence: str) -> bool:
        s = sentence.lower()
        patterns = [
            r'at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)',
            r'at\s+\d{1,2}\s*(?:am|pm)',
            r'at\s+(morning|afternoon|evening|noon|midnight)',
            r'\d{1,2}:\d{2}\s*(?:am|pm)',
            r'\d{1,2}\s*(?:am|pm)',
            r'(morning|afternoon|evening|noon|midnight)(?!\s+(?:at|in|on))',
            r'sharp',
        ]
        return any(re.search(p, s) for p in patterns)

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

        at_time_patterns = [
            r'at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)',
            r'at\s+\d{1,2}\s*(?:am|pm)',
            r'at\s+(morning|afternoon|evening|noon|midnight)',
        ]
        has_at_time = any(re.search(p, s) for p in at_time_patterns)

        other_time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:am|pm)',
            r'\d{1,2}\s*(?:am|pm)',
            r'(morning|afternoon|evening|noon|midnight)(?!\s+(?:at|in|on))',
            r'sharp',
        ]
        has_other_time = any(re.search(p, s) for p in other_time_patterns)
        has_explicit_time = has_at_time or has_other_time
        has_recurrent     = any(kw in s for kw in RECURRENT_KEYWORDS)

        if has_recurrent:
            schema["recurrent"]["value"]      = True
            schema["fixed_time"]["value"]     = False
            schema["fixed_start"]["value"]    = None

            # Extract abstract time label for recurrent tasks
            time_label = None
            if "morning" in s:
                time_label = "morning"
            elif "evening" in s:
                time_label = "evening"
            elif "night" in s:
                time_label = "night"
            elif "afternoon" in s:
                time_label = "afternoon"
            elif "noon" in s:
                time_label = "noon"

            # Set start and deadline to the abstract label (or null if not specified)
            if time_label:
                schema["start"]["value"]     = time_label
                schema["start"]["predicted"] = False
                schema["deadline"]["value"]  = time_label
            else:
                schema["start"]["value"]     = None
                schema["deadline"]["value"]  = None

            if "every day" in s or "daily" in s:
                schema["recurrence_days"]["value"] = DAYS.copy()
            elif "weekday" in s:
                schema["recurrence_days"]["value"] = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
            else:
                mentioned = [DAYS_LOWER[d] for d in DAYS_LOWER if d in s]
                schema["recurrence_days"]["value"] = mentioned if mentioned else random.sample(DAYS, k=random.randint(1, 3))

        elif has_explicit_time:
            schema["fixed_time"]["value"]  = True
            schema["start"]["value"]       = None
            schema["deadline"]["value"]    = None

            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))|(morning|afternoon|evening|noon)', s)
            if time_match:
                time_str = time_match.group(0)
                if   "morning"   in time_str: schema["fixed_start"]["value"] = "08:00"
                elif "afternoon" in time_str: schema["fixed_start"]["value"] = "13:00"
                elif "evening"   in time_str: schema["fixed_start"]["value"] = "18:00"
                elif "noon"      in time_str: schema["fixed_start"]["value"] = "12:00"
                else:                         schema["fixed_start"]["value"] = time_str.strip()

        if "today" in s and not has_recurrent and not has_explicit_time:
            if schema["start"]["value"] is None:
                schema["start"]["value"]     = "today"
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

        s = sentence.lower()
        has_explicit_time = (
            "sharp" in s or
            re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', s) is not None or
            any(w in s for w in ("morning", "afternoon", "evening", "noon")) or
            re.search(r'at\s+\d{1,2}', s) is not None
        )
        if not has_explicit_time and schema["fixed_time"]["value"]:
            schema["fixed_time"]["value"]  = False
            schema["fixed_start"]["value"] = None

        return f"add: {sentence}", schema_to_pipe(schema)

    def _generate_modify(self):
        sentence, placeholder_map = self._fill_template()
        existing = self._build_schema(placeholder_map, sentence)

        # Sample 1–3 changes (richer variety now that we have more templates)
        num_changes    = random.randint(1, 3)
        sampled        = random.sample(CHANGE_TEMPLATES, k=num_changes)
        changed_fields = {}
        change_phrases = []

        for field_name, phrase_fn, value_fn in sampled:
            new_value = value_fn()
            change_phrases.append(phrase_fn(new_value))

            # Handle paired fields
            if field_name == "fixed_time+fixed_start":
                changed_fields["fixed_time"]  = {"value": True}
                changed_fields["fixed_start"] = {"value": new_value}
            elif field_name == "recurrent+recurrence_days":
                changed_fields["recurrent"]       = {"value": True}
                changed_fields["recurrence_days"] = {"value": new_value}
            else:
                changed_fields[field_name] = {"value": new_value}

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
    arg_parser.add_argument("--modify-only", action="store_true",
                            help="Preview modify-only samples instead of mixed")
    args = arg_parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")

    yp = VMAI_YamlParser(os.path.join(cfg_path, vars.SYNTHETIC_DATASET))
    yp.load_yaml()
    training_data = yp.parse()

    rp = VMAI_RealDataParser(os.path.join(cfg_path, vars.REAL_DATASET))
    rp.load_yaml()
    real_data = rp.parse()

    gen = DataGenerator(training_data, real_data)

    if args.modify_only:
        ds = gen.generate_modify_only(args.sentences)
    else:
        ds = gen.generate(args.sentences)

    for i in range(min(100, len(ds))):
        print("IN: ", ds["input_text"][i])
        print("OUT:", ds["target_text"][i])
        print()