"""
    VM.AI Balanced Data Generator
    Creates balanced training data from templates and placeholders
    Ensures equal distribution across all field types

    Written by: Vanea @ 25-03-2026
"""

import vars
import json
import random
import argparse
import re
from datasets import Dataset
from collections import defaultdict

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

# Realistic difficulty mappings
DIFFICULTY_MAP = {
    "easy": 0.15, "simple": 0.2, "light": 0.25, "quick": 0.3,
    "moderate": 0.5, "medium": 0.55,
    "hard": 0.75, "difficult": 0.8, "challenging": 0.85, "intense": 0.9, "complex": 0.85
}

# Realistic importance mappings
IMPORTANCE_MAP = {
    "low": 0.2, "not urgent": 0.25, "minor": 0.3,
    "medium": 0.5, "important": 0.7, "critical": 0.85,
    "urgent": 0.9, "asap": 0.92, "emergency": 0.95
}

CHANGE_TEMPLATES = [
    ("duration",   lambda v: f"make it {v} minutes", lambda: str(random.randint(15, 180))),
    ("deadline",   lambda v: f"push deadline to {v}", lambda: random.choice(["Sunday", "next Monday", "Friday", "tomorrow"])),
    ("location",   lambda v: f"do it at {v}", lambda: random.choice(["home", "office", "gym", "library", "online"])),
    ("difficulty", lambda v: f"it's a {'hard' if float(v) > 0.5 else 'light'} session", lambda: str(round(random.uniform(0.1, 0.95), 2))),
    ("importance", lambda v: f"it's {'very important' if float(v) > 0.5 else 'not urgent'}", lambda: str(round(random.uniform(0.1, 0.99), 2))),
]


def schema_to_pipe(schema: dict) -> str:
    """Convert schema dict to pipe-separated string"""
    parts = []
    for field, entry in schema.items():
        val = entry["value"]
        if val is None:
            continue
        if isinstance(val, bool):
            parts.append(f"{field}={'true' if val else 'false'}")
        elif isinstance(val, list):
            parts.append(f"{field}={','.join(val)}")
        else:
            parts.append(f"{field}={val}")
    return " | ".join(parts)


def normalize_time(time_str: str) -> str:
    """Convert various time formats to HH:MM format"""
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    
    # Handle "5pm", "5:30pm" format
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
    
    # Handle "5:00" format (24h)
    match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Handle relative times
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
    
    return time_str


def normalize_duration(duration_str: str) -> str:
    """Convert duration to integer minutes"""
    if not duration_str:
        return None
    
    duration_str = str(duration_str).lower().strip()
    
    # Extract numbers
    numbers = re.findall(r'(\d+(?:\.\d+)?)', duration_str)
    if not numbers:
        return None
    
    value = float(numbers[0])
    
    # Convert hours to minutes
    if "hour" in duration_str or "hr" in duration_str:
        return str(int(value * 60))
    
    # Already in minutes
    if "minute" in duration_str or "min" in duration_str:
        return str(int(value))
    
    # Just a number - assume minutes if <= 180, hours if > 180
    if value <= 180:
        return str(int(value))
    else:
        return str(int(value * 60))


def get_difficulty_value(keyword: str) -> str:
    """Map difficulty keyword to numeric value"""
    keyword = keyword.lower()
    for k, v in DIFFICULTY_MAP.items():
        if k in keyword:
            return str(v)
    # Default random between 0.4 and 0.6
    return str(round(random.uniform(0.4, 0.6), 2))


def get_importance_value(keyword: str) -> str:
    """Map importance keyword to numeric value"""
    keyword = keyword.lower()
    for k, v in IMPORTANCE_MAP.items():
        if k in keyword:
            return str(v)
    # Default random between 0.4 and 0.6
    return str(round(random.uniform(0.4, 0.6), 2))


class DataGenerator:
    def __init__(self, training_data, real_examples=None, specific_examples=None):
        self.training_data = training_data
        self.real_examples = real_examples or []
        self.specific_examples = specific_examples or []
        
        # Templates for each type (ensure variety)
        self.task_templates = training_data.templates if training_data else [
            "[TASK]",
            "need to [TASK]",
            "remember to [TASK]",
            "don't forget to [TASK]",
            "schedule [TASK]",
            "plan to [TASK]",
            "i have to [TASK]",
            "must [TASK]",
        ]
        
        self.all_placeholders = training_data.get_placeholder_map() if training_data else {}
        
        # Track counts for balance
        self.generated_counts = defaultdict(int)
    
    def generate(self, max_examples=10000):
        """Generate balanced dataset"""
        
        # Calculate how many of each type we need
        add_types = ["flexible", "fixed_time", "recurrent", "location_only", "deadline_only", 
                     "duration_only", "difficulty_only", "importance_only", "combined"]
        examples_per_type = max_examples // len(add_types)
        
        data = {"input_text": [], "target_text": []}
        
        # Generate each type
        generation_strategies = [
            ("flexible", self._generate_flexible),
            ("fixed_time", self._generate_fixed_time),
            ("recurrent", self._generate_recurrent),
            ("location_only", self._generate_location_only),
            ("deadline_only", self._generate_deadline_only),
            ("duration_only", self._generate_duration_only),
            ("difficulty_only", self._generate_difficulty_only),
            ("importance_only", self._generate_importance_only),
            ("combined", self._generate_combined),
        ]
        
        for target_type, generator in generation_strategies:
            target = examples_per_type
            for _ in range(target):
                inp, tgt = generator()
                data["input_text"].append(inp)
                data["target_text"].append(tgt)
                self.generated_counts[target_type] += 1
        
        # Generate modify examples
        modify_count = max_examples // 4
        for _ in range(modify_count):
            inp, tgt = self._generate_modify()
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        
        # Add real examples if any
        for example in self.real_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        
        for example in self.specific_examples:
            inp, tgt = self._convert_real(example)
            data["input_text"].append(inp)
            data["target_text"].append(tgt)
        
        # Shuffle
        combined = list(zip(data["input_text"], data["target_text"]))
        random.shuffle(combined)
        data["input_text"], data["target_text"] = zip(*combined)
        
        self._print_report(modify_count)
        
        return Dataset.from_dict(data)
    
    def _print_report(self, modify_count):
        print("\n" + "="*60)
        print("BALANCED DATA GENERATION REPORT")
        print("="*60)
        print("\nADD EXAMPLES:")
        for type_name, count in sorted(self.generated_counts.items()):
            print(f"  {type_name:15} : {count}")
        print(f"\nMODIFY EXAMPLES: {modify_count}")
        print(f"TOTAL: {sum(self.generated_counts.values()) + modify_count}")
        print("="*60)
    
    def _get_task_name(self):
        """Get a random task name from templates"""
        if self.all_placeholders.get("TASK"):
            return random.choice(self.all_placeholders["TASK"])
        return random.choice(["task", "work", "project", "meeting", "call", "email", "report"])
    
    def _get_location(self):
        """Get a random location"""
        if self.all_placeholders.get("LOCATION"):
            return random.choice(self.all_placeholders["LOCATION"])
        return random.choice(["home", "office", "gym", "library", "coffee shop", "school"])
    
    def _generate_flexible(self):
        """Task with no time, no deadline, just a task"""
        task = self._get_task_name()
        
        templates = [
            f"{task}",
            f"do {task}",
            f"need to {task}",
            f"remember {task}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["fixed_time"]["value"] = False
        schema["recurrent"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_fixed_time(self):
        """Task with explicit time"""
        task = self._get_task_name()
        
        times = ["at 9am", "at 2pm", "at 5:30pm", "at 8am sharp", "at noon", "at 3pm", "at 6am", "at 11:30am", "in the morning", "in the afternoon"]
        time_str = random.choice(times)
        
        templates = [
            f"{task} {time_str}",
            f"{time_str} {task}",
            f"schedule {task} {time_str}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["fixed_time"]["value"] = True
        schema["start"]["value"] = None
        schema["fixed_start"]["value"] = normalize_time(time_str)
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_recurrent(self):
        """Recurring task"""
        task = self._get_task_name()
        
        patterns = [
            "every day", "daily", "every weekday",
            "every Monday", "every Tuesday and Thursday",
            "every Monday Wednesday Friday", "weekly",
        ]
        recurrence = random.choice(patterns)
        
        # Optionally add time
        if random.random() < 0.3:
            times = [" at 9am", " at 5pm", " in the morning", " in the evening"]
            recurrence += random.choice(times)
        
        templates = [
            f"{task} {recurrence}",
            f"{recurrence} {task}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["recurrent"]["value"] = True
        schema["fixed_time"]["value"] = False
        
        # Set recurrence days
        s = sentence.lower()
        if "every day" in s or "daily" in s:
            schema["recurrence_days"]["value"] = DAYS.copy()
        elif "weekday" in s:
            schema["recurrence_days"]["value"] = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
        else:
            mentioned = [DAYS_LOWER[d] for d in DAYS_LOWER if d in s]
            if mentioned:
                schema["recurrence_days"]["value"] = mentioned
        
        # Check for time
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))|(morning|afternoon|evening|noon)', sentence.lower())
        if time_match and random.random() < 0.5:
            schema["fixed_time"]["value"] = True
            schema["fixed_start"]["value"] = normalize_time(time_match.group(0))
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_location_only(self):
        """Task with location but no time"""
        task = self._get_task_name()
        location = self._get_location()
        
        templates = [
            f"{task} at {location}",
            f"at {location}, {task}",
            f"do {task} at {location}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["location"]["value"] = location
        schema["fixed_time"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_deadline_only(self):
        """Task with deadline"""
        task = self._get_task_name()
        
        deadlines = ["by Friday", "by tomorrow", "by next week", "by Monday", "before the weekend", "by end of day", "by tonight"]
        deadline = random.choice(deadlines)
        
        templates = [
            f"{task} {deadline}",
            f"{deadline}, {task}",
            f"submit {task} {deadline}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        deadline_val = deadline.replace("by ", "").replace("before ", "")
        schema["deadline"]["value"] = deadline_val
        schema["fixed_time"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_duration_only(self):
        """Task with duration"""
        task = self._get_task_name()
        
        durations = ["for 30 minutes", "takes 1 hour", "for 45 minutes", "2 hours", "15 minutes", "90 minutes", "for 3 hours"]
        duration = random.choice(durations)
        
        templates = [
            f"{task} {duration}",
            f"{duration} {task}",
            f"block {duration} for {task}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["duration"]["value"] = normalize_duration(duration)
        schema["fixed_time"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_difficulty_only(self):
        """Task with difficulty level"""
        task = self._get_task_name()
        
        difficulties = ["easy", "simple", "hard", "difficult", "challenging", "light work", "intense", "complex"]
        difficulty = random.choice(difficulties)
        
        templates = [
            f"{task}, {difficulty}",
            f"{difficulty} {task}",
            f"this {task} is {difficulty}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["difficulty"]["value"] = get_difficulty_value(difficulty)
        schema["fixed_time"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_importance_only(self):
        """Task with importance level"""
        task = self._get_task_name()
        
        importances = ["urgent", "important", "critical", "low priority", "not urgent", "asap", "high priority"]
        importance = random.choice(importances)
        
        templates = [
            f"{task}, {importance}",
            f"{importance}: {task}",
            f"this is {importance}, {task}",
        ]
        sentence = random.choice(templates)
        
        schema = self._create_base_schema(task)
        schema["importance"]["value"] = get_importance_value(importance)
        schema["fixed_time"]["value"] = False
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_combined(self):
        """Task with multiple fields combined"""
        task = self._get_task_name()
        sentence = task
        
        schema = self._create_base_schema(task)
        schema["fixed_time"]["value"] = False
        
        # Add 2-3 fields
        fields = []
        
        if random.random() < 0.5:
            location = self._get_location()
            fields.append(f"at {location}")
            schema["location"]["value"] = location
        
        if random.random() < 0.5:
            deadlines = ["by Friday", "by tomorrow", "by Monday", "by next week"]
            deadline = random.choice(deadlines)
            fields.append(deadline)
            schema["deadline"]["value"] = deadline.replace("by ", "")
        
        if random.random() < 0.5:
            durations = ["30 minutes", "1 hour", "2 hours", "45 minutes"]
            duration = random.choice(durations)
            fields.append(f"takes {duration}")
            schema["duration"]["value"] = normalize_duration(duration)
        
        if random.random() < 0.5:
            difficulties = ["easy", "hard", "challenging"]
            difficulty = random.choice(difficulties)
            fields.append(difficulty)
            schema["difficulty"]["value"] = get_difficulty_value(difficulty)
        
        if random.random() < 0.5:
            importances = ["urgent", "important", "critical"]
            importance = random.choice(importances)
            fields.append(importance)
            schema["importance"]["value"] = get_importance_value(importance)
        
        if random.random() < 0.3:
            times = ["at 9am", "at 2pm", "in the morning"]
            time_str = random.choice(times)
            fields.append(time_str)
            schema["fixed_time"]["value"] = True
            schema["fixed_start"]["value"] = normalize_time(time_str)
            schema["start"]["value"] = None
        
        random.shuffle(fields)
        sentence = f"{task}, " + ", ".join(fields) if fields else task
        
        return f"add: {sentence}", schema_to_pipe(schema)
    
    def _generate_modify(self):
        """Generate modify example"""
        # Create a base task first
        task = self._get_task_name()
        schema = self._create_base_schema(task)
        
        # Randomly add some fields to make it realistic
        if random.random() < 0.5:
            schema["location"]["value"] = self._get_location()
        if random.random() < 0.3:
            schema["duration"]["value"] = str(random.randint(30, 120))
        if random.random() < 0.3:
            schema["difficulty"]["value"] = str(round(random.uniform(0.3, 0.7), 2))
        
        # Pick a field to modify
        modify_fields = ["duration", "deadline", "location", "difficulty", "importance"]
        field_to_modify = random.choice(modify_fields)
        
        if field_to_modify == "duration":
            new_value = str(random.randint(15, 180))
            change_phrase = f"make it {new_value} minutes"
        elif field_to_modify == "deadline":
            new_value = random.choice(["tomorrow", "Friday", "Monday", "next week"])
            change_phrase = f"push deadline to {new_value}"
        elif field_to_modify == "location":
            new_value = random.choice(["home", "office", "gym", "library", "online"])
            change_phrase = f"do it at {new_value}"
        elif field_to_modify == "difficulty":
            new_value = "hard" if random.random() > 0.5 else "easy"
            change_phrase = f"make it {new_value}"
        else:  # importance
            new_value = "urgent" if random.random() > 0.5 else "not urgent"
            change_phrase = f"make it {new_value}"
        
        # Build existing task summary
        existing_summary = {}
        for k, v in schema.items():
            if v["value"] is not None:
                existing_summary[k] = v["value"]
        
        input_text = f"modify: {json.dumps(existing_summary, ensure_ascii=False)} \u2502 {change_phrase}"
        target_text = f"{field_to_modify}={new_value}"
        
        return input_text, target_text
    
    def _create_base_schema(self, task_name):
        """Create base schema with task name and default predicted fields"""
        return {
            "name":            {"value": task_name, "predicted": False},
            "start":           {"value": None, "predicted": True},
            "deadline":        {"value": None, "predicted": False},
            "difficulty":      {"value": None, "predicted": True},
            "duration":        {"value": None, "predicted": True},
            "category":        {"value": None, "predicted": True},
            "location":        {"value": None, "predicted": True},
            "importance":      {"value": None, "predicted": True},
            "fixed_time":      {"value": False, "predicted": False},
            "fixed_start":     {"value": None, "predicted": False},
            "recurrent":       {"value": False, "predicted": False},
            "recurrence_days": {"value": None, "predicted": False},
        }
    
    def _convert_real(self, example: dict):
        """Convert real example to pipe format"""
        sentence = example["input"]
        output = example["output"]
        
        if sentence.startswith("modify:"):
            parts = []
            for k, v in output.items():
                if v is not None:
                    # Normalize values
                    if k == "fixed_start":
                        v = normalize_time(v)
                    elif k == "duration":
                        v = normalize_duration(v)
                    parts.append(f"{k}={v}")
            return sentence, " | ".join(parts)
        
        schema = {
            "name":            {"value": output.get("name"), "predicted": False},
            "start":           {"value": output.get("start"), "predicted": False},
            "deadline":        {"value": output.get("deadline"), "predicted": False},
            "difficulty":      {"value": output.get("difficulty"), "predicted": True},
            "duration":        {"value": normalize_duration(output.get("duration")) if output.get("duration") else None, "predicted": True},
            "category":        {"value": output.get("category"), "predicted": True},
            "location":        {"value": output.get("location"), "predicted": True},
            "importance":      {"value": output.get("importance"), "predicted": True},
            "fixed_time":      {"value": output.get("fixed_time", False), "predicted": False},
            "fixed_start":     {"value": normalize_time(output.get("fixed_start")) if output.get("fixed_start") else None, "predicted": False},
            "recurrent":       {"value": output.get("recurrent", False), "predicted": False},
            "recurrence_days": {"value": output.get("recurrence_days"), "predicted": False},
        }
        
        return f"add: {sentence.lower().strip()}", schema_to_pipe(schema)


if __name__ == "__main__":
    from yaml_parser import VMAI_YamlParser, VMAI_RealDataParser
    import os

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--sentences", type=int, default=1000)
    arg_parser.add_argument("--output", type=str, default=None)
    args = arg_parser.parse_args()

    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")

    # Load training data for templates
    yp = VMAI_YamlParser(os.path.join(cfg_path, vars.SYNTHETIC_DATASET))
    yp.load_yaml()
    training_data = yp.parse()

    # Load real examples if available
    real_data = []
    if os.path.exists(os.path.join(cfg_path, vars.REAL_DATASET)):
        try:
            rp = VMAI_RealDataParser(os.path.join(cfg_path, vars.REAL_DATASET))
            rp.load_yaml()
            real_data = rp.parse()
            print(f"Loaded {len(real_data)} real examples")
        except:
            print("Could not load real data, continuing without")

    generator = DataGenerator(training_data, real_data)
    dataset = generator.generate(args.sentences)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            for i in range(min(200, len(dataset))):
                f.write(f"IN: {dataset['input_text'][i]}\n")
                f.write(f"OUT: {dataset['target_text'][i]}\n\n")
        print(f"\nSaved first 200 examples to {args.output}")
    else:
        for i in range(min(50, len(dataset))):
            print("IN: ", dataset["input_text"][i])
            print("OUT:", dataset["target_text"][i])
            print()