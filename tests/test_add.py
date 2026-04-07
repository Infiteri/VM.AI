import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parser'))
from chat import TaskPlannerPredictor

def g(s, f):
    e = s.get(f, {})
    return e.get("value") if isinstance(e, dict) else e

p = TaskPlannerPredictor()
passed = 0; failed = 0
def c(n, ok, d=""):
    global passed, failed
    if ok: passed += 1; print(f"  PASS | {n}")
    else: failed += 1; print(f"  FAIL | {n} | {d}")

print("="*80); print("  ADD MODE TESTS"); print("="*80)

tests = [
    ("gym at 6am",          "category",      "fitness"),
    ("pay the rent",        "category",      "finance"),
    ("file the taxes",      "category",      "finance"),
    ("meditate",            "category",      "health"),
    ("go to the doctor",    "category",      "health"),
    ("study for the exam",  "category",      "study"),
    ("grocery shopping",    "category",      "shopping"),
    ("write blog post",     "category",      "creative"),
    ("book flight to Paris","category",      "travel"),
    ("team meeting",        "category",      "work"),
    ("practice guitar",     "category",      "creative"),
    ("pick up kids",        "category",      "family"),
    ("call mom",            "category",      "personal"),

    ("hard workout",        "difficulty",    0.7, ">"),
    ("easy stretch",        "difficulty",    0.3, "<"),
    ("challenging coding",  "difficulty",    0.65, ">"),
    ("moderate task",       "difficulty",    0.35, ">"),
    ("pay the rent",        "difficulty",    0.3, "<"),
    ("file the taxes",      "difficulty",    0.5, ">"),
    ("urgent client call",  "difficulty",    0.6, ">"),
    ("critical crash fix",  "difficulty",    0.7, ">"),
    ("low priority cleanup","difficulty",    0.4, "<"),

    ("urgent client call",  "importance",    0.7, ">"),
    ("critical crash fix",  "importance",    0.85, ">"),
    ("low priority cleanup","importance",    0.4, "<"),
    ("very important",      "importance",    0.6, ">"),
    ("pay the rent",        "importance",    0.7, ">"),
    ("file the taxes",      "importance",    0.7, ">"),
    ("optional task",       "importance",    0.3, "<"),
    ("asap fix needed",     "importance",    0.7, ">"),
    ("not urgent reading",  "importance",    0.35, "<"),

    ("quick 5 minute",      "duration",      5, "=="),
    ("15 minute meditation","duration",      15, "=="),
    ("2 hour study session","duration",      120, "=="),
    ("pay the rent",        "duration",      5, ">"),
    ("team meeting",        "duration",      15, ">"),
    ("go to the doctor",    "duration",      30, ">"),
    ("critical crash",      "duration",      60, ">"),
    ("workout session",     "duration",      30, ">"),
    ("go for a run",        "duration",      15, ">"),
    ("cook dinner",         "duration",      30, ">"),

    ("gym at 6am",          "fixed_time",    True),
    ("team meeting at 3pm", "fixed_start",   "15:00"),
    ("doctor at 10:30am",   "fixed_start",   "10:30"),
    ("dinner at 7pm",       "fixed_start",   "19:00"),

    ("meditate every morning","recurrent",   True),
    ("daily standup every weekday","recurrent", True),
    ("gym every Monday and Wednesday","recurrent", True),

    ("study at the library",    "location",  "library"),
    ("meet at the coffee shop", "location",  "coffee shop"),
    ("buy groceries at the supermarket","location","supermarket"),
    ("work from home",          "location",  "home"),
    ("team meeting at the office","location","office"),

    ("gym at 6am",          "name",      "gym"),
    ("pay the utility bill","name",      "bill"),
    ("book a flight to Paris","name",    "flight"),
    ("write a blog post about AI","name","blog"),
]

for t in tests:
    if len(t) == 4:
        inp, field, exp = t[0], t[1], t[2]
        op = None
    elif len(t) == 5:
        inp, field, exp, op = t
    else:
        continue

    result = p.predict_add(inp)
    actual = g(result, field)

    if op == ">":
        try: ok = actual is not None and float(actual) > exp
        except: ok = False
    elif op == "<":
        try: ok = actual is not None and float(actual) < exp
        except: ok = False
    elif op == "==":
        try: ok = actual is not None and abs(float(actual) - exp) < 0.2
        except: ok = False
    elif isinstance(exp, bool):
        ok = actual == exp
    else:
        ok = actual is not None and exp.lower() in str(actual).lower()

    c(f"add: '{inp[:40]}' -> {field}={exp}", ok, f"got={actual}")

print(f"\n{'='*80}")
print(f"  RESULTS: {passed}/{passed+failed} passed ({100*passed//(passed+failed)}%)")
print(f"{'='*80}")
sys.exit(0 if failed==0 else 1)
