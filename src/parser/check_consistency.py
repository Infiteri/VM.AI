"""
    VM.AI - Consistency Check Script
    Runs the same inputs every time to track model progress.
    Usage: python src/check_consistency.py

    Soft checks: looks for keywords in output, not exact matches.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chat import TaskPlannerPredictor
import re

print("Loading model...")
p = TaskPlannerPredictor()
print()

# ── Add Tests (Rule-Based) ──────────────────────────────────────────────────
print("=" * 60)
print("  ADD MODE (Rule-Based)")
print("=" * 60)

add_tests = [
    ("gym at 6am",             {"fixed_time": True, "fixed_start": "06:00"}),
    ("meeting at 3pm",         {"fixed_start": "15:00"}),
    ("meditate",               {"category": "health"}),
    ("pay the rent",           {"category": "finance"}),
    ("grocery shopping",       {"category": "shopping"}),
    ("hard workout",           {"difficulty": 0.8}),
    ("easy task",              {"difficulty": 0.3}),
    ("urgent fix",             {"importance": 0.9}),
    ("low priority reading",   {"importance": 0.3}),
    ("gym every monday",       {"recurrent": True}),
    ("study at the library",   {"location": "library"}),
    ("work from home",         {"location": "home"}),
    ("30 minute stretch",      {"duration": 30}),
    ("2 hour study session",   {"duration": 120}),
    ("pay bill tomorrow",      {"deadline": "tomorrow"}),
    ("finish report by friday",{"deadline": "Friday"}),
]

def get_val(result, field):
    e = result.get(field, {})
    return e.get("value") if isinstance(e, dict) else e

def soft_check(result, expected):
    for field, exp in expected.items():
        val = get_val(result, field)
        if val is None:
            return False, f"{field}=None (exp {exp})"
        if isinstance(exp, bool):
            if val != exp:
                return False, f"{field}={val} (exp {exp})"
        elif isinstance(exp, (int, float)):
            try:
                if float(val) < exp * 0.5:  # very loose threshold
                    return False, f"{field}={val} (exp >{exp*0.5})"
            except:
                return False, f"{field}='{val}' (exp ~{exp})"
        else:
            if str(exp).lower() not in str(val).lower():
                return False, f"{field}='{val}' (exp '{exp}')"
    return True, ""

ap = 0; af = 0
for inp, checks in add_tests:
    result = p.predict_add(inp)
    ok, detail = soft_check(result, checks)
    if ok: ap += 1
    else:
        af += 1
        print(f"  FAIL | {inp:30s} | {detail}")

print(f"\nAdd: {ap}/{len(add_tests)} PASS")

# ── Modify Tests (Model) ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  MODIFY MODE (Model)")
print("=" * 60)

mod_tests = [
    ("push deadline to friday",     "deadline", "friday"),
    ("move deadline to next week",  "deadline", "week"),
    ("set it for 3pm",              "fixed_start", "15:00"),
    ("at 10:30am instead",          "fixed_start", "10:30"),
    ("cancel fixed time",           "fixed_time", "false"),
    ("make it 90 minutes",          "duration", "90"),
    ("make it 15 minutes",          "duration", "15"),
    ("make it harder",              "difficulty", 0.5),
    ("make it easier",              "difficulty", 0.4, "<"),
    ("make it urgent",              "importance", 0.7),
    ("make it low priority",        "importance", 0.4, "<"),
    ("do it at home instead",       "location", "home"),
    ("categorize it as fitness",    "category", "fitness"),
    ("change to work",              "category", "work"),
    ("make it repeat every monday", "recurrent", "true"),
    ("cancel recurrence",           "recurrent", "false"),
    ("start on monday",             "start", "monday"),
]

base_task = {
    "name": {"value": "gym session", "predicted": False},
    "difficulty": {"value": "0.5", "predicted": True},
    "duration": {"value": "60", "predicted": True},
    "category": {"value": "fitness", "predicted": True},
    "importance": {"value": "0.5", "predicted": True},
    "fixed_time": {"value": False, "predicted": False},
    "fixed_start": {"value": None, "predicted": False},
    "deadline": {"value": "tomorrow", "predicted": False},
    "start": {"value": None, "predicted": True},
    "location": {"value": "gym", "predicted": True},
    "recurrent": {"value": False, "predicted": False},
    "recurrence_days": {"value": None, "predicted": True},
}

mp = 0; mf = 0
for inp, field, exp, *extra in mod_tests:
    result = p.predict_modify(base_task, inp)
    raw = p._last_raw_output

    # Check raw output first (model might output correct format but diff logic misses it)
    raw_ok = False
    if field + "=" in raw.lower():
        raw_val = raw.lower().split(field + "=")[1].split("[")[0].split("|")[0].split("<")[0].strip()
        if isinstance(exp, str):
            raw_ok = exp.lower() in raw_val
        elif isinstance(exp, (int, float)):
            try:
                rv = float(raw_val)
                op = extra[0] if extra else "=="
                if op == "<": raw_ok = rv < exp
                else: raw_ok = rv > exp * 0.5
            except: raw_ok = False

    val = get_val(result, field)
    op = extra[0] if extra else "=="
    ok = raw_ok
    if not ok and val is not None:
        if isinstance(exp, bool):
            ok = val == exp
        elif isinstance(exp, str):
            ok = str(exp).lower() in str(val).lower()
        elif isinstance(exp, (int, float)):
            try:
                rv = float(val)
                if op == "<": ok = rv < exp
                else: ok = rv > exp * 0.5
            except: ok = False

    if ok: mp += 1
    else:
        mf += 1
        print(f"  FAIL | {inp:35s} | {field}={val} | raw: {raw[:70]}")

print(f"\nModify: {mp}/{len(mod_tests)} PASS")
print(f"\n{'='*60}")
print(f"  TOTAL: {ap+mp}/{len(add_tests)+len(mod_tests)} ({100*(ap+mp)//(len(add_tests)+len(mod_tests))}%)")
print(f"{'='*60}")
