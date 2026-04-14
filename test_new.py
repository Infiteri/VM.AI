"""Test new model with new format."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'parser'))
import torch
from transformers import AutoTokenizer, T5ForConditionalGeneration
from schemas import pipe_to_schema

MODEL = r"models\finetuned_parser"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Loading {MODEL} on {device}...")
tok = AutoTokenizer.from_pretrained(MODEL)
mdl = T5ForConditionalGeneration.from_pretrained(MODEL).to(device)
mdl.eval()

def run(inp):
    ids = tok(inp, return_tensors="pt", truncation=True, padding=True).to(device)
    with torch.no_grad():
        out = mdl.generate(ids["input_ids"], attention_mask=ids["attention_mask"],
                           max_new_tokens=128, min_length=0,
                           no_repeat_ngram_size=3, repetition_penalty=1.2)
    return tok.decode(out[0], skip_special_tokens=True)

print("=" * 80)
print("  ADD TESTS")
print("=" * 80)
add_tests = [
    "urgent gym session tomorrow at 9am for 60 minutes",
    "easy study session for 30 minutes",
    "hard coding task at the office",
    "pay the electricity bill tomorrow",
    "meditate for 15 minutes in the morning",
    "daily workout every weekday at 7am",
    "buy groceries at the supermarket",
    "critical bug fix ASAP",
    "team meeting at the office every tuesday",
    "book a flight to paris for next week",
]
for s in add_tests:
    raw = run(f"add: {s}")
    sc = pipe_to_schema(raw, input_text=s)
    issues = []
    garbage = [t for t in ["EXPLODED","EXCLUDED","EYE","EXC","EXL","EYP","PRDB","PRDE","PRDD","falsity","truly"] if t in raw]
    if garbage: issues.append(f"garbage: {garbage}")
    if "." in raw and " | " in raw: issues.append("mixed sep")
    status = "FAIL" if issues else "PASS"
    print(f"[{status}] {s[:50]:50s}")
    if issues:
        print(f"       Raw: {raw[:140]}")
        for i in issues: print(f"       -> {i}")

print("\n" + "=" * 80)
print("  MODIFY TESTS")
print("=" * 80)
base = {"name":{"value":"gym session","predicted":False},"difficulty":{"value":"0.5","predicted":True},"duration":{"value":"60","predicted":True},"category":{"value":"fitness","predicted":True},"importance":{"value":"0.5","predicted":True},"fixed_time":{"value":False,"predicted":False},"fixed_start":{"value":None,"predicted":False},"deadline":{"value":"tomorrow","predicted":False},"start":{"value":None,"predicted":True},"location":{"value":"gym","predicted":True},"recurrent":{"value":False,"predicted":False},"recurrence_days":{"value":None,"predicted":True}}
mod_tests = [
    "push deadline to friday",
    "make it harder",
    "change duration to 90 minutes",
    "do it at home instead",
    "set it for 3pm",
    "categorize it as work",
    "start on monday",
    "make it very important",
    "cancel recurrence",
    "make it 15 minutes",
]
for s in mod_tests:
    raw = run(s.lower())
    sc = pipe_to_schema(raw, input_text=s)
    issues = []
    garbage = [t for t in ["EXPLODED","EXCLUDED","EYE","EXC","EXL","EYP","PRDB","PRDE","PRDD","falsity","truly"] if t in raw]
    if garbage: issues.append(f"garbage: {garbage}")
    if "." in raw and " | " in raw: issues.append("mixed sep")
    if "error" in sc: issues.append(f"parse fail: {raw[:80]}")
    status = "FAIL" if issues else "PASS"
    print(f"[{status}] {s:45s}")
    if issues:
        print(f"       Raw: {raw[:140]}")
        for i in issues: print(f"       -> {i}")

print("\n" + "=" * 80)
