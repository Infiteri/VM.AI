"""
    VM.AI - Comprehensive Pre-Training Sanitization Test
    Validates ALL components before final training commit.
    Run from ROOT: python tests/test_sanitize.py
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parser'))

from schemas import (
    schema_to_pipe, pipe_to_schema, changed_to_pipe,
    normalize_time, normalize_duration, normalize_deadline,
    detect_explicit_fields, parse_pipe_simple
)
from vars import PREDICTED_FIELDS, ALWAYS_EXPLICIT, ALL_FIELDS, VALID_CATEGORIES, DAYS

# ─── Test Infrastructure ─────────────────────────────────────────────────────
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            self.errors.append({"name": name, "detail": detail})
            print(f"  ❌ {name} | {detail}")

results = TestResult()

# ─── SECTION 1: Schema Generation with Tags ──────────────────────────────────
print("\n" + "="*80)
print("SECTION 1: SCHEMA GENERATION & TAGS")
print("="*80)

# Test 1.1: EXP tags for explicit fields
schema1 = {
    'name': {'value': 'fix bug', 'predicted': False},
    'difficulty': {'value': '0.9', 'predicted': False},
    'importance': {'value': '0.95', 'predicted': False},
    'category': {'value': 'work', 'predicted': True},
    'duration': {'value': '60', 'predicted': True},
}
pipe1 = schema_to_pipe(schema1)
results.check("1.1: EXP tags in output", "[EXP]" in pipe1 and "[PRD]" in pipe1, pipe1)
results.check("1.1: Name is EXP", "name=fix bug[EXP]" in pipe1)
results.check("1.1: Difficulty is EXP", "difficulty=0.9[EXP]" in pipe1)
results.check("1.1: Category is PRD", "category=work[PRD]" in pipe1)

# Test 1.2: All PRD tags
schema2 = {
    'name': {'value': 'gym', 'predicted': False},
    'difficulty': {'value': '0.5', 'predicted': True},
    'importance': {'value': '0.5', 'predicted': True},
    'category': {'value': 'fitness', 'predicted': True},
}
pipe2 = schema_to_pipe(schema2)
results.check("1.2: Difficulty is PRD", "difficulty=0.5[PRD]" in pipe2)
results.check("1.2: Importance is PRD", "importance=0.5[PRD]" in pipe2)

# Test 1.3: Pipe parsing with tags
parsed = pipe_to_schema(pipe1, input_text="hard urgent task")
results.check("1.3: Parse difficulty tag", parsed.get('difficulty', {}).get('predicted') == False)
results.check("1.3: Parse category tag", parsed.get('category', {}).get('predicted') == True)

# Test 1.4: Pipe parsing without tags (fallback to keyword detection)
pipe_no_tags = "name=gym | difficulty=0.6 | category=fitness"
parsed_no_tags = pipe_to_schema(pipe_no_tags, input_text="hard workout")
results.check("1.4: No-tag fallback detects EXP", parsed_no_tags.get('difficulty', {}).get('predicted') == False)

# ─── SECTION 2: Data Generator Output ────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 2: DATA GENERATOR OUTPUT FORMAT")
print("="*80)

try:
    from data_generator import DataGenerator
    from yaml_parser import VMAI_YamlParser
    import vars
    
    # Load synthetic data
    yp = VMAI_YamlParser(f"./data/{vars.SYNTHETIC_DATASET}")
    yp.load_yaml()
    training_data = yp.parse()
    gen = DataGenerator(training_data)
    
    # Test 2.1: Add generation format
    inp, tgt = gen._generate_add()
    results.check("2.1: Add output has tags", "[EXP]" in tgt or "[PRD]" in tgt, tgt[:50])
    results.check("2.1: Add input starts with 'add:'", inp.startswith("add:"))
    
    # Test 2.2: Modify generation format
    inp_mod, tgt_mod = gen._generate_modify()
    results.check("2.2: Modify output has tags", "[EXP]" in tgt_mod or "[PRD]" in tgt_mod, tgt_mod[:50])
    results.check("2.2: Modify input starts with 'modify:'", inp_mod.startswith("modify:"))
    
    # Test 2.3: Multiple samples validation
    tag_errors = 0
    for _ in range(20):
        _, t = gen._generate_add()
        parts = t.split("|")
        for part in parts:
            if "[" not in part or "]" not in part:
                tag_errors += 1
    results.check("2.3: All samples have tags", tag_errors == 0, f"Found {tag_errors} parts without tags")
    
except Exception as e:
    results.check("2.X: Generator Import", False, str(e))

# ─── SECTION 3: Validation Logic ─────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 3: VALIDATION LOGIC")
print("="*80)

# Test 3.1: Valid pipe with tags
valid_pipe = "name=test[EXP] | difficulty=0.5[PRD] | category=work[PRD]"
parsed_valid = pipe_to_schema(valid_pipe)
results.check("3.1: Valid pipe parses correctly", parsed_valid.get('name', {}).get('value') == 'test')

# Test 3.2: Invalid pipe (no tags) still works
invalid_pipe = "name=test | difficulty=0.5"
parsed_invalid = pipe_to_schema(invalid_pipe)
results.check("3.2: Invalid pipe fallback works", parsed_invalid.get('name', {}).get('value') == 'test')

# Test 3.3: Tag consistency check
from validate_dataset import validate_consistency
errors = validate_consistency("urgent task", "difficulty=0.9[EXP] | importance=0.95[EXP]", 0)
results.check("3.3: Consistency validation works", len(errors) == 0, f"Found {len(errors)} errors")

# ─── SECTION 4: Chat Interface ───────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 4: CHAT INTERFACE")
print("="*80)

# Test 4.1: Pipe to schema with tags
try:
    from chat import TaskPlannerPredictor
    # We can't fully test chat without model, but we can test parsing
    from schemas import pipe_to_schema
    
    test_pipe = "name=gym[EXP] | fixed_start=06:00[EXP] | category=fitness[PRD]"
    parsed_chat = pipe_to_schema(test_pipe, input_text="gym at 6am")
    results.check("4.1: Chat parsing handles tags", parsed_chat.get('name', {}).get('predicted') == False)
    results.check("4.1: Chat parsing detects EXP", parsed_chat.get('fixed_start', {}).get('predicted') == False)
    
except Exception as e:
    results.check("4.X: Chat Import", False, str(e))

# ─── SECTION 5: Training Script Compatibility ────────────────────────────────
print("\n" + "="*80)
print("SECTION 5: TRAINING SCRIPT COMPATIBILITY")
print("="*80)

# Test 5.1: Pipe parsing for metrics (tags should be stripped)
try:
    from train import _parse_pipe_with_tags
    
    test_pipe = "name=gym[EXP] | difficulty=0.5[PRD]"
    parsed_train = _parse_pipe_with_tags(test_pipe)
    results.check("5.1: Training parser strips tags", parsed_train.get('difficulty') == '0.5')
    results.check("5.1: Training parser gets name", parsed_train.get('name') == 'gym')
    
except Exception as e:
    results.check("5.X: Training Import", False, str(e))

# ─── SECTION 6: Data Integrity ───────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 6: DATA INTEGRITY")
print("="*80)

# Test 6.1: Real data format
try:
    import yaml
    
    with open("./data/VMAI_REAL_Data.yaml", "r") as f:
        real_data = yaml.safe_load(f)
    
    examples = real_data.get("examples", [])
    add_count = sum(1 for e in examples if not e.get("input", "").startswith("modify:"))
    mod_count = sum(1 for e in examples if e.get("input", "").startswith("modify:"))
    
    results.check("6.1: Real data has examples", len(examples) > 0, f"Found {len(examples)} examples")
    results.check("6.1: Add examples exist", add_count > 0, f"Found {add_count} add examples")
    results.check("6.1: Modify examples exist", mod_count > 0, f"Found {mod_count} modify examples")
    
    # Check first add example structure
    add_ex = next((e for e in examples if not e.get("input", "").startswith("modify:")), None)
    if add_ex:
        out = add_ex.get("output", {})
        results.check("6.1: Add example has required fields", 
                     "category" in out and "difficulty" in out and "importance" in out)
    
except Exception as e:
    results.check("6.X: Real Data Load", False, str(e))

# ─── SECTION 7: Keyword Detection ────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 7: KEYWORD DETECTION")
print("="*80)

# Test 7.1: Difficulty keywords
diff_tests = [
    ("hard workout", True),
    ("easy task", True),
    ("moderate difficulty", True),
    ("gym session", False),  # No difficulty keyword
]
for text, expected in diff_tests:
    explicit = detect_explicit_fields(text)
    results.check(f"7.1: '{text}' difficulty detection", 
                 ("difficulty" in explicit) == expected, 
                 f"Got {explicit}")

# Test 7.2: Importance keywords
imp_tests = [
    ("urgent meeting", True),
    ("critical fix", True),
    ("low priority task", True),
    ("go to gym", False),
]
for text, expected in imp_tests:
    explicit = detect_explicit_fields(text)
    results.check(f"7.2: '{text}' importance detection", 
                 ("importance" in explicit) == expected, 
                 f"Got {explicit}")

# Test 7.3: Time keywords
time_tests = [
    ("gym at 6am", {"fixed_time", "fixed_start"}),
    ("meeting at 3pm", {"fixed_time", "fixed_start"}),
    ("workout", set()),
]
for text, expected_fields in time_tests:
    explicit = detect_explicit_fields(text)
    results.check(f"7.3: '{text}' time detection", 
                 expected_fields.issubset(explicit), 
                 f"Got {explicit}, expected {expected_fields}")

# ─── SECTION 8: Normalization ────────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 8: NORMALIZATION FUNCTIONS")
print("="*80)

# Test 8.1: Time normalization
time_tests = [
    ("6am", "06:00"),
    ("3pm", "15:00"),
    ("12:30pm", "12:30"),
    ("morning", "08:00"),
    ("invalid", None),
]
for inp, expected in time_tests:
    result = normalize_time(inp)
    results.check(f"8.1: Time '{inp}' -> '{expected}'", result == expected, f"Got {result}")

# Test 8.2: Duration normalization
dur_tests = [
    ("60", "60"),
    ("2 hours", "120"),
    ("30 minutes", "30"),
    ("invalid", None),
]
for inp, expected in dur_tests:
    result = normalize_duration(inp)
    results.check(f"8.2: Duration '{inp}' -> '{expected}'", result == expected, f"Got {result}")

# ─── SECTION 9: Cross-Component Consistency ──────────────────────────────────
print("\n" + "="*80)
print("SECTION 9: CROSS-COMPONENT CONSISTENCY")
print("="*80)

# Test 9.1: Generator output can be parsed by chat interface
try:
    from data_generator import DataGenerator
    from yaml_parser import VMAI_YamlParser
    import vars
    
    yp = VMAI_YamlParser(f"./data/{vars.SYNTHETIC_DATASET}")
    yp.load_yaml()
    gen = DataGenerator(yp.parse())
    
    for _ in range(5):
        inp, tgt = gen._generate_add()
        # Try to parse it
        parsed = pipe_to_schema(tgt, input_text=inp)
        if not parsed.get('name', {}).get('value'):
            results.check("9.1: Generator->Chat compatibility", False, f"Failed to parse: {tgt}")
            break
    else:
        results.check("9.1: Generator->Chat compatibility", True)
        
except Exception as e:
    results.check("9.X: Cross-component test", False, str(e))

# ─── SECTION 10: Edge Cases ──────────────────────────────────────────────────
print("\n" + "="*80)
print("SECTION 10: EDGE CASES")
print("="*80)

# Test 10.1: Empty pipe
empty_parsed = pipe_to_schema("")
results.check("10.1: Empty pipe handling", empty_parsed.get('name', {}).get('value') is None)

# Test 10.2: Pipe with only tags
tags_only = "name=test[EXP]"
parsed_tags = pipe_to_schema(tags_only)
results.check("10.2: Tags-only parsing", parsed_tags.get('name', {}).get('value') == 'test')
results.check("10.2: Tags-only EXP detection", parsed_tags.get('name', {}).get('predicted') == False)

# Test 10.3: Mixed valid/invalid parts
mixed_pipe = "name=test[EXP] | invalid_field | difficulty=0.5[PRD]"
parsed_mixed = pipe_to_schema(mixed_pipe)
results.check("10.3: Mixed pipe handling", parsed_mixed.get('name', {}).get('value') == 'test')

# ─── FINAL REPORT ────────────────────────────────────────────────────────────
print("\n" + "="*80)
print("SANITIZATION REPORT")
print("="*80)

total = results.passed + results.failed
pct = (results.passed / total * 100) if total > 0 else 0

print(f"\nTotal Tests: {total}")
print(f"Passed: {results.passed}")
print(f"Failed: {results.failed}")
print(f"Success Rate: {pct:.1f}%")

if results.errors:
    print(f"\n⚠️  FAILURES DETECTED:")
    for err in results.errors:
        print(f"  - {err['name']}: {err['detail']}")

if results.failed == 0:
    print("\n✅ ALL TESTS PASSED - CODEBASE IS SANITIZED AND READY FOR TRAINING")
else:
    print(f"\n❌ {results.failed} TEST(S) FAILED - REVIEW ISSUES BEFORE TRAINING")

print("\n" + "="*80)

sys.exit(0 if results.failed == 0 else 1)
