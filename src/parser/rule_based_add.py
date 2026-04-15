"""
    VM-AI - Rule-based Add Mode Parser (MVP)
    Extracts basic fields from natural language without a model.
"""

import re
from vars import ALL_FIELDS, DAYS

def normalize_time(time_str):
    if not time_str: return None
    time_str = str(time_str).strip().lower()
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if m.group(3) == "pm" and h != 12: h += 12
        elif m.group(3) == "am" and h == 12: h = 0
        return f"{h:02d}:{mi:02d}"
    if "morning" in time_str: return "08:00"
    if "afternoon" in time_str: return "13:00"
    if "evening" in time_str: return "18:00"
    if "noon" in time_str: return "12:00"
    if "midnight" in time_str: return "00:00"
    return None

def parse_add(sentence: str) -> dict:
    s = sentence.lower().strip()
    schema = {f: {"value": ALL_FIELDS[f], "predicted": True} for f in ALL_FIELDS}
    schema["name"]["predicted"] = False
    schema["fixed_time"]["predicted"] = False
    schema["fixed_start"]["predicted"] = False
    schema["recurrent"]["predicted"] = False
    schema["recurrence_days"]["predicted"] = False

    # Always set predicted defaults (model always outputs these)
    schema["difficulty"]["value"] = "0.5"
    schema["importance"]["value"] = "0.5"
    schema["category"]["value"] = "personal"
    schema["duration"]["value"] = "30"
    schema["location"]["value"] = None

    # Name
    name = s
    for prefix in ["i need to ", "i have to ", "i want to ", "schedule ", "set ", "create ", "remind me to "]:
        if name.startswith(prefix): name = name[len(prefix):]
    for kw in [" at ", " by ", " for ", " every ", " from ", " with ", " to "]:
        idx = name.find(kw)
        if idx > 0: name = name[:idx]
    schema["name"]["value"] = name.strip()

    # Fixed time
    tm = re.search(r'at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))', s)
    if tm:
        n = normalize_time(tm.group(1))
        if n:
            schema["fixed_time"]["value"] = True
            schema["fixed_start"]["value"] = n

    # Duration (override default if explicit)
    dm = re.search(r'(\d+(?:\.\d+)?)\s*(?:minute|min|hour|hr)s?', s)
    if dm:
        v = float(dm.group(1))
        if "hour" in s or "hr" in s: v *= 60
        schema["duration"]["value"] = str(int(v))
        schema["duration"]["predicted"] = False

    # Recurrence
    if "every " in s or "daily" in s or "each " in s:
        schema["recurrent"]["value"] = True
        days = [d for d in DAYS if d.lower() in s]
        if not days:
            if "weekday" in s: days = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
            elif "daily" in s or "every day" in s: days = DAYS[:]
        if days:
            schema["recurrence_days"]["value"] = ",".join(days)

    # Difficulty (override default if keyword match)
    for kw, val in [("hard",0.85),("difficult",0.85),("challenging",0.8),("tough",0.75),
                    ("easy",0.15),("simple",0.15),("light",0.2),("quick",0.2),("moderate",0.45)]:
        if kw in s:
            schema["difficulty"]["value"] = str(val)
            schema["difficulty"]["predicted"] = False
            break

    # Importance (override default if keyword match)
    for kw, val in [("urgent",0.95),("critical",0.95),("asap",0.95),("very important",0.9),
                    ("important",0.75),("low priority",0.15),("not urgent",0.2),("optional",0.2)]:
        if kw in s:
            schema["importance"]["value"] = str(val)
            schema["importance"]["predicted"] = False
            break

    # Deadline
    if "tomorrow" in s: schema["deadline"]["value"] = "tomorrow"
    elif "next week" in s: schema["deadline"]["value"] = "next week"
    else:
        for d in DAYS:
            if d.lower() in s and "every" not in s.split(d.lower())[0][-6:]:
                schema["deadline"]["value"] = d
                break

    # Location (override default if keyword match)
    for kw, loc in [("at the library","library"),("at the gym","gym"),("at the office","office"),
                    ("at home","home"),("from home","home"),("at the coffee shop","coffee shop"),
                    ("at the supermarket","supermarket")]:
        if kw in s:
            schema["location"]["value"] = loc
            schema["location"]["predicted"] = False
            break

    # Category (override default if keyword match)
    for kw, cat in [("gym","fitness"),("yoga","fitness"),("workout","fitness"),
                    ("meditat","health"),("doctor","health"),("study","study"),("exam","study"),
                    ("rent","finance"),("tax","finance"),("bill","finance"),("invoice","finance"),
                    ("clean","home"),("laundry","home"),("call mom","personal"),("kids","family"),
                    ("flight","travel"),("hotel","travel"),("guitar","creative"),("blog","creative"),
                    ("spanish","learning"),("grocery","shopping"),("meeting","work"),
                    ("standup","work"),("code","work"),("coding","work")]:
        if kw in s:
            schema["category"]["value"] = cat
            schema["category"]["predicted"] = False
            break

    return schema
