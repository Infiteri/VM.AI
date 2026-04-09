"""
    VM-AI - Data Generator with EXP/PRD Tag Support
    Generates training data in pipe format with explicit/predicted tags:
    name=gym[EXP] | difficulty=0.6[PRD] | category=fitness[PRD]
    Run: python src/parser/data_generator.py
"""

import vars
import json
import random
import argparse
import re
from datasets import Dataset
from schemas import (
    schema_to_pipe, changed_to_pipe, normalize_duration, 
    normalize_deadline, normalize_time, clamp_category,
    detect_explicit_fields, DIFFICULTY_KEYWORDS, IMPORTANCE_KEYWORDS,
    CATEGORY_KEYWORDS, DURATION_KEYWORDS, TIME_KEYWORDS, RECURRENCE_KEYWORDS
)

PREDICTED_FIELDS = vars.PREDICTED_FIELDS
FIELD_MAP = vars.FIELD_MAP if hasattr(vars, 'FIELD_MAP') else {}
DAYS = vars.DAYS
DAYS_LOWER = {d.lower(): d for d in DAYS}

# ── Random Generators ────────────────────────────────────────────────────────
def _rand_duration():
    return str(random.choice([10, 15, 20, 25, 30, 45, 60, 90, 120, 150, 180]))

def _rand_deadline():
    return random.choice(["Sunday", "next Monday", "Friday", "tomorrow", "next week", "this weekend", "Wednesday", "Thursday"])

def _rand_location():
    return random.choice(["home", "office", "gym", "library", "online", "school", "the coffee shop", "the park"])

def _rand_difficulty():
    return str(round(random.uniform(0.1, 0.95), 2))

def _rand_importance():
    return str(round(random.uniform(0.1, 0.99), 2))

def _rand_category():
    return random.choice(list(vars.VALID_CATEGORIES))

def _rand_name():
    return random.choice(["finish the report", "review the document", "send the email", "prepare the presentation", "call the client", "fix the bug"])

def _rand_time():
    return random.choice(["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"])

def _rand_recurrence_days():
    count = random.randint(1, 3)
    return ",".join(random.sample(DAYS, k=count))

# ── CHANGE_TEMPLATES ──────────────────────────────────────────────────────────

CHANGE_TEMPLATES = [
    ("duration", lambda v: f"make it {v} minutes", _rand_duration),
    ("duration", lambda v: f"change duration to {v} minutes", _rand_duration),
    ("duration", lambda v: f"it should take {v} minutes", _rand_duration),
    ("deadline", lambda v: f"push deadline to {v}", _rand_deadline),
    ("deadline", lambda v: f"move the deadline to {v}", _rand_deadline),
    ("location", lambda v: f"do it at {v}", _rand_location),
    ("location", lambda v: f"change location to {v}", _rand_location),
    ("difficulty", lambda v: f"mark it as {'hard' if float(v) > 0.5 else 'easy'}", _rand_difficulty),
    ("importance", lambda v: f"mark it as {'high priority' if float(v) > 0.5 else 'low priority'}", _rand_importance),
    ("category", lambda v: f"categorize it as {v}", _rand_category),
    ("name", lambda v: f"rename it to {v}", _rand_name),
    ("fixed_time+fixed_start", lambda v: f"set it for {v}", _rand_time),
    ("cancel_fixed_time", lambda v: "cancel fixed time", lambda: "false"),
    ("recurrent+recurrence_days", lambda v: f"make it repeat every {v}", _rand_recurrence_days),
    ("cancel_recurrent", lambda v: "cancel recurrence", lambda: "false"),
]


class DataGenerator:
    def __init__(self, training_data, real_examples=None, specific_examples=None):
        self.training_data = training_data
        self.real_examples = real_examples or []
        self.specific_examples = specific_examples or []

    def generate(self, max_examples=10000):
        """Generate mixed add+modify dataset with EXP/PRD tags."""
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
        data = {"input_text": [], "target_text": []}
        for _ in range(max_examples):
            inp, tgt = self._generate_modify_full()
            data["input_text"].append(inp)
            data["target_text"].append(tgt)

        for example in self.real_examples + self.specific_examples:
            if not isinstance(example.get("input"), str):
                continue
            if example["input"].startswith("modify:"):
                inp, tgt = self._convert_real_modify_full(example)
                for _ in range(3):
                    data["input_text"].append(inp)
                    data["target_text"].append(tgt)
        return Dataset.from_dict(data)

    def _fill_template(self):
        templates = self.training_data.templates
        all_placeholders = self.training_data.get_placeholder_map()
        template = random.choice(templates)
        sentence = template
        placeholder_map = {}
        for ph, options in all_placeholders.items():
            tag = f"[{ph}]"
            while tag in sentence:
                value = str(random.choice(options))
                sentence = sentence.replace(tag, value)
                placeholder_map[ph] = value
        return sentence.lower().strip(), placeholder_map

    # ── Keyword-based Inference ───────────────────────────────────────────────

    _TASK_CATEGORY_MAP = {
        "migration": "work", "deploy": "work", "refactor": "work", "optimize": "work",
        "code": "work", "bug": "work", "crash": "work", "fix": "work",
        "presentation": "work", "meeting": "work", "standup": "work",
        "report": "work", "email": "work", "client": "work", "invoice": "work",
        "exam": "study", "homework": "study", "lecture": "study",
        "thesis": "study", "assignment": "study", "tutor": "study",
        "study session": "study", "study": "study",
        "gym": "fitness", "run": "fitness", "yoga": "fitness",
        "workout": "fitness", "swim": "fitness", "cycle": "fitness",
        "doctor": "health", "medication": "health", "dentist": "health",
        "meditate": "health", "prescription": "health",
        "rent": "finance", "bill": "finance", "tax": "finance", "taxes": "finance",
        "bank": "finance", "payment": "finance",
        "clean": "home", "laundry": "home", "cook": "home",
        "dinner": "home", "lunch": "home", "breakfast": "home",
        "call mom": "personal", "call dad": "personal",
        "kids": "family", "children": "family",
        "friend": "social", "party": "social", "movie": "social",
        "flight": "travel", "hotel": "travel", "passport": "travel",
        "guitar": "creative", "draw": "creative", "blog": "creative",
        "spanish": "learning", "piano": "learning", "learn": "learning",
        "groceries": "shopping", "gift": "shopping", "buy": "shopping",
        "shopping": "shopping", "supermarket": "shopping",
        "return": "errands", "package": "errands",
        "password": "admin", "backup": "admin", "config": "admin",
    }

    def _infer_category(self, sentence: str) -> str:
        s = sentence.lower()
        for keyword in sorted(self._TASK_CATEGORY_MAP.keys(), key=len, reverse=True):
            if re.search(r'\b' + re.escape(keyword) + r'\b', s):
                return self._TASK_CATEGORY_MAP[keyword]
        return random.choice(["work", "personal", "home", "errands"])

    def _infer_difficulty(self, sentence: str) -> str:
        s = sentence.lower()
        # Use local keywords since imported ones are sets
        local_keywords = {"hard": 0.8, "difficult": 0.85, "challenging": 0.8, "complex": 0.75, "intense": 0.9, "heavy": 0.85, "tough": 0.75, "urgent": 0.75, "easy": 0.15, "simple": 0.2, "light": 0.25, "quick": 0.2, "moderate": 0.5, "medium": 0.5}
        for keyword, val in local_keywords.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', s):
                return str(round(val + random.uniform(-0.05, 0.05), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["crash", "bug", "fix", "emergency", "critical", "taxes", "tax", "exam"]):
            return str(round(random.uniform(0.6, 0.85), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["workout", "gym", "heavy", "hard"]):
            return str(round(random.uniform(0.6, 0.85), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["report", "presentation", "study"]):
            return str(round(random.uniform(0.5, 0.7), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["quick", "easy", "simple", "stretch"]):
            return str(round(random.uniform(0.1, 0.25), 2))
        return str(round(random.uniform(0.3, 0.6), 2))

    def _infer_importance(self, sentence: str) -> str:
        s = sentence.lower()
        # Use local keywords since imported ones are sets
        local_keywords = {"urgent": 0.9, "critical": 0.95, "asap": 0.92, "emergency": 0.98, "important": 0.75, "high priority": 0.8, "must": 0.85, "low priority": 0.2, "not urgent": 0.2, "minor": 0.25, "can wait": 0.3, "whenever": 0.15, "optional": 0.15}
        for keyword, val in local_keywords.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', s):
                return str(round(val + random.uniform(-0.05, 0.05), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["crash", "emergency", "critical", "urgent", "asap", "taxes", "rent", "bill", "pay", "exam"]):
            return str(round(random.uniform(0.8, 0.95), 2))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["meeting", "presentation", "report"]):
            return str(round(random.uniform(0.5, 0.7), 2))
        return str(round(random.uniform(0.4, 0.6), 2))

    def _infer_duration(self, sentence: str) -> str:
        s = sentence.lower()
        match = re.search(r'(\d+)\s*(?:minute|min|hour|hr)', s)
        if match:
            val = int(match.group(1))
            if "hour" in s or "hr" in s:
                return str(val * 60)
            return str(val)
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["crash", "bug", "fix"]):
            return str(random.choice([60, 90, 120]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["report", "presentation"]):
            return str(random.choice([60, 90, 120]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["workout", "gym", "yoga"]):
            return str(random.choice([45, 60, 90]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["meeting", "call"]):
            return str(random.choice([15, 30, 45, 60]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["run", "jog", "stretch"]):
            return str(random.choice([15, 30, 45]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["meditate", "meditation"]):
            return str(random.choice([10, 15, 20]))
        if any(re.search(r'\b' + re.escape(w) + r'\b', s) for w in ["pay", "bill", "rent", "tax"]):
            return str(random.choice([5, 10, 15]))
        return str(random.choice([30, 45, 60]))

    def _infer_location(self, sentence: str) -> str | None:
        s = sentence.lower()
        locs = {"at the library": "library", "at the gym": "gym", "at home": "home", 
                "from home": "home", "at the coffee shop": "coffee shop", 
                "at the office": "office", "at the supermarket": "supermarket"}
        for phrase, loc in sorted(locs.items(), key=len, reverse=True):
            if phrase in s:
                return loc
        return None

    def _build_schema(self, placeholder_map, sentence=""):
        s = sentence.lower()
        explicit_fields = detect_explicit_fields(sentence)
        
        schema = {
            "name": {"value": None, "predicted": "name" not in explicit_fields},
            "start": {"value": None, "predicted": "start" not in explicit_fields},
            "deadline": {"value": None, "predicted": "deadline" not in explicit_fields},
            "difficulty": {"value": None, "predicted": "difficulty" not in explicit_fields},
            "duration": {"value": None, "predicted": "duration" not in explicit_fields},
            "category": {"value": None, "predicted": "category" not in explicit_fields},
            "location": {"value": None, "predicted": "location" not in explicit_fields},
            "importance": {"value": None, "predicted": "importance" not in explicit_fields},
            "fixed_time": {"value": False, "predicted": "fixed_time" not in explicit_fields},
            "fixed_start": {"value": None, "predicted": "fixed_start" not in explicit_fields},
            "recurrent": {"value": False, "predicted": "recurrent" not in explicit_fields},
            "recurrence_days": {"value": None, "predicted": "recurrence_days" not in explicit_fields},
        }

        for yaml_key, value in placeholder_map.items():
            field = FIELD_MAP.get(yaml_key)
            if not field:
                continue
            if field in PREDICTED_FIELDS:
                continue
            schema[field]["value"] = value
            schema[field]["predicted"] = False

        # Always infer predicted fields from sentence content
        schema["category"]["value"] = self._infer_category(s)
        schema["difficulty"]["value"] = self._infer_difficulty(s)
        schema["importance"]["value"] = self._infer_importance(s)
        schema["duration"]["value"] = self._infer_duration(s)
        
        loc = self._infer_location(s)
        if loc:
            schema["location"]["value"] = loc

        # Handle time/explicit time
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', s)
        if time_match:
            schema["fixed_time"]["value"] = True
            schema["fixed_start"]["value"] = normalize_time(time_match.group(0))
            schema["start"]["value"] = None
            schema["deadline"]["value"] = None

        # Handle recurrence
        if any(kw in s for kw in ["every", "daily", "each", "weekday"]):
            schema["recurrent"]["value"] = True
            if "every day" in s or "daily" in s:
                schema["recurrence_days"]["value"] = DAYS.copy()
            elif "weekday" in s:
                schema["recurrence_days"]["value"] = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
            else:
                mentioned = [DAYS_LOWER[d] for d in DAYS_LOWER if d in s]
                schema["recurrence_days"]["value"] = mentioned if mentioned else random.sample(DAYS, k=random.randint(1, 3))

        # Handle deadline/start keywords
        for d in DAYS:
            if d.lower() in s:
                schema["deadline"]["value"] = d
                break
        if "tomorrow" in s:
            schema["deadline"]["value"] = "tomorrow"
        if "next week" in s:
            schema["deadline"]["value"] = "next week"

        # Update predicted flags based on what was actually found
        for field in ["fixed_time", "fixed_start", "recurrent", "recurrence_days", "deadline", "start"]:
            if schema[field]["value"] is not None and schema[field]["value"] is not False:
                schema[field]["predicted"] = False
            elif field in ["fixed_time", "recurrent"] and schema[field]["value"] is False:
                schema[field]["predicted"] = False

        return schema

    def _generate_add(self):
        sentence, placeholder_map = self._fill_template()
        schema = self._build_schema(placeholder_map, sentence)
        return f"add: {sentence}", schema_to_pipe(schema)

    def _generate_modify(self):
        sentence, placeholder_map = self._fill_template()
        existing = self._build_schema(placeholder_map, sentence)
        num_changes = random.randint(1, 3)
        sampled = random.sample(CHANGE_TEMPLATES, k=num_changes)
        changed_fields = {}
        change_phrases = []

        for field_name, phrase_fn, value_fn in sampled:
            new_value = value_fn()
            change_phrases.append(phrase_fn(new_value))
            if field_name == "fixed_time+fixed_start":
                changed_fields["fixed_time"] = {"value": True, "predicted": False}
                changed_fields["fixed_start"] = {"value": normalize_time(new_value), "predicted": False}
            elif field_name == "recurrent+recurrence_days":
                changed_fields["recurrent"] = {"value": True, "predicted": False}
                changed_fields["recurrence_days"] = {"value": new_value, "predicted": False}
            elif field_name == "cancel_fixed_time":
                changed_fields["fixed_time"] = {"value": False, "predicted": False}
                changed_fields["fixed_start"] = {"value": None, "predicted": False}
            elif field_name == "cancel_recurrent":
                changed_fields["recurrent"] = {"value": False, "predicted": False}
                changed_fields["recurrence_days"] = {"value": None, "predicted": False}
            else:
                changed_fields[field_name] = {"value": new_value, "predicted": True}

        existing_summary = {k: v["value"] for k, v in existing.items() if v["value"] is not None}
        input_text = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} \u2502 {', '.join(change_phrases)}"
        return input_text, changed_to_pipe(changed_fields)

    def _generate_modify_full(self):
        sentence, placeholder_map = self._fill_template()
        existing = self._build_schema(placeholder_map, sentence)
        num_changes = random.randint(1, 3)
        sampled = random.sample(CHANGE_TEMPLATES, k=num_changes)
        changed_fields = {}
        change_phrases = []

        for field_name, phrase_fn, value_fn in sampled:
            new_value = value_fn()
            change_phrases.append(phrase_fn(new_value))
            if field_name == "fixed_time+fixed_start":
                changed_fields["fixed_time"] = {"value": True}
                changed_fields["fixed_start"] = {"value": normalize_time(new_value)}
            elif field_name == "recurrent+recurrence_days":
                changed_fields["recurrent"] = {"value": True}
                changed_fields["recurrence_days"] = {"value": new_value}
            elif field_name == "cancel_fixed_time":
                changed_fields["fixed_time"] = {"value": False}
                changed_fields["fixed_start"] = {"value": None}
            else:
                changed_fields[field_name] = {"value": new_value}

        task = dict(existing)
        for k, v in changed_fields.items():
            if isinstance(v, dict):
                task[k] = v["value"]
            else:
                task[k] = v

        schema = {
            "name": {"value": task.get("name"), "predicted": False},
            "start": {"value": task.get("start"), "predicted": False},
            "deadline": {"value": task.get("deadline"), "predicted": False},
            "difficulty": {"value": task.get("difficulty"), "predicted": True},
            "duration": {"value": task.get("duration"), "predicted": True},
            "category": {"value": task.get("category"), "predicted": True},
            "location": {"value": task.get("location"), "predicted": True},
            "importance": {"value": task.get("importance"), "predicted": True},
            "fixed_time": {"value": task.get("fixed_time", False), "predicted": False},
            "fixed_start": {"value": task.get("fixed_start"), "predicted": False},
            "recurrent": {"value": task.get("recurrent", False), "predicted": False},
            "recurrence_days": {"value": task.get("recurrence_days"), "predicted": False},
        }

        input_text = f"modify: {json.dumps({k: v for k, v in existing.items() if v['value'] is not None}, ensure_ascii=False)} \u2502 {', '.join(change_phrases)}"
        return input_text, schema_to_pipe(schema)

    def _convert_real(self, example: dict):
        sentence = example["input"]
        output = example["output"]

        if sentence.startswith("modify:"):
            parts = []
            for k, v in output.items():
                if v is not None:
                    if isinstance(v, bool):
                        v = "true" if v else "false"
                    if k == "duration":
                        v = normalize_duration(v) or v
                    if k == "fixed_start":
                        v = normalize_time(str(v)) or v
                    if k in ("deadline", "start"):
                        v = normalize_deadline(v)
                    if k == "category":
                        v = clamp_category(v)
                    if k in ("difficulty", "importance"):
                        try:
                            v = str(round(float(v), 2))
                        except (ValueError, TypeError):
                            pass
                    parts.append(f"{k}={v}")
            return sentence, " | ".join(parts)

        # Detect explicit fields from input
        explicit_fields = detect_explicit_fields(sentence)
        
        difficulty = output.get("difficulty")
        if difficulty is None:
            difficulty = self._infer_difficulty(sentence)
            explicit_fields.discard("difficulty")
        else:
            difficulty = str(round(float(difficulty), 2))

        importance = output.get("importance")
        if importance is None:
            importance = self._infer_importance(sentence)
            explicit_fields.discard("importance")
        else:
            importance = str(round(float(importance), 2))

        category = output.get("category")
        if category is None:
            category = self._infer_category(sentence)
            explicit_fields.discard("category")
        else:
            category = clamp_category(category)

        duration = output.get("duration")
        if duration is None:
            duration = self._infer_duration(sentence)
            explicit_fields.discard("duration")
        else:
            duration = normalize_duration(duration) or self._infer_duration(sentence)

        start = output.get("start")
        if start is not None:
            start = normalize_deadline(start)

        deadline = output.get("deadline")
        if deadline is not None:
            deadline = normalize_deadline(deadline)

        fixed_start = output.get("fixed_start")
        if fixed_start is not None:
            fixed_start = normalize_time(fixed_start)

        schema = {
            "name": {"value": output.get("name"), "predicted": "name" not in explicit_fields},
            "start": {"value": start, "predicted": "start" not in explicit_fields},
            "deadline": {"value": deadline, "predicted": "deadline" not in explicit_fields},
            "difficulty": {"value": difficulty, "predicted": "difficulty" not in explicit_fields},
            "duration": {"value": duration, "predicted": "duration" not in explicit_fields},
            "category": {"value": category, "predicted": "category" not in explicit_fields},
            "location": {"value": output.get("location"), "predicted": "location" not in explicit_fields},
            "importance": {"value": importance, "predicted": "importance" not in explicit_fields},
            "fixed_time": {"value": output.get("fixed_time", False), "predicted": "fixed_time" not in explicit_fields},
            "fixed_start": {"value": fixed_start, "predicted": "fixed_start" not in explicit_fields},
            "recurrent": {"value": output.get("recurrent", False), "predicted": "recurrent" not in explicit_fields},
            "recurrence_days": {"value": output.get("recurrence_days"), "predicted": "recurrence_days" not in explicit_fields},
        }

        return f"add: {sentence.lower().strip()}", schema_to_pipe(schema)

    def _convert_real_modify_full(self, example: dict):
        sentence = example["input"]
        output = example["output"]

        try:
            json_str = sentence.replace("modify:", "").split("\u2502")[0].strip()
            original = json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            return sentence, ""

        task = dict(original)
        for k, v in output.items():
            if v is not None:
                if isinstance(v, bool):
                    task[k] = "true" if v else "false"
                elif k == "duration":
                    task[k] = normalize_duration(v) or v
                elif k == "fixed_start":
                    task[k] = normalize_time(str(v)) or v
                elif k in ("deadline", "start"):
                    task[k] = normalize_deadline(v) or v
                elif k == "category":
                    task[k] = clamp_category(v)
                elif k in ("difficulty", "importance"):
                    try:
                        task[k] = str(round(float(v), 2))
                    except (ValueError, TypeError):
                        task[k] = v
                else:
                    task[k] = v
            else:
                task.pop(k, None)

        schema = {
            "name": {"value": task.get("name"), "predicted": False},
            "start": {"value": task.get("start"), "predicted": False},
            "deadline": {"value": task.get("deadline"), "predicted": False},
            "difficulty": {"value": task.get("difficulty"), "predicted": True},
            "duration": {"value": task.get("duration"), "predicted": True},
            "category": {"value": task.get("category"), "predicted": True},
            "location": {"value": task.get("location"), "predicted": True},
            "importance": {"value": task.get("importance"), "predicted": True},
            "fixed_time": {"value": task.get("fixed_time", False), "predicted": False},
            "fixed_start": {"value": task.get("fixed_start"), "predicted": False},
            "recurrent": {"value": task.get("recurrent", False), "predicted": False},
            "recurrence_days": {"value": task.get("recurrence_days"), "predicted": False},
        }

        return sentence, schema_to_pipe(schema)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=int, default=10)
    args = parser.parse_args()

    from yaml_parser import VMAI_YamlParser
    yp = VMAI_YamlParser(f"./data/{vars.SYNTHETIC_DATASET}")
    yp.load_yaml()
    training_data = yp.parse()
    gen = DataGenerator(training_data)

    for _ in range(args.sentences):
        inp, tgt = gen._generate_add()
        print(f"IN:  {inp}")
        print(f"OUT: {tgt}")
        print()
