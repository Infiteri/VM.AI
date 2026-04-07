"""
    VM-AI - Automated Test Suite for Chat Interface
    Runs Add and Modify tests, captures outputs for comparison.
    Run: python tests/test_chat_suite.py

    Written by: Vanea
"""

import sys
import os
import subprocess
import json
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parser'))

# Define test cases
ADD_TESTS = [
    "gym at 6am",
    "pay the rent",
    "file the taxes",
    "grocery shopping",
    "hard workout session",
    "easy 15 minute stretch",
    "urgent client call",
    "critical system crash fix",
    "low priority cleanup",
    "moderate difficulty task",
    "team meeting at 3pm",
    "meditate every morning",
]

MODIFY_TESTS = [
    # (existing_task_json, change_prompt)
    ({"name": "gym", "fixed_time": True, "fixed_start": "06:00", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "recurrent": False}, "move to 7am"),
    ({"name": "workout", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "make it harder"),
    ({"name": "client call", "importance": 0.5, "duration": 30, "category": "work", "difficulty": 0.3, "fixed_time": False, "recurrent": False}, "make it urgent"),
    ({"name": "yoga", "category": "work", "duration": 60, "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "categorize it as fitness"),
    ({"name": "meeting", "fixed_time": True, "fixed_start": "14:00", "duration": 30, "category": "work", "difficulty": 0.2, "importance": 0.6, "recurrent": False}, "make it 1 hour"),
]

def run_test_phase(tests_add, tests_modify, phase_name):
    print(f"\n{'='*80}")
    print(f"  PHASE: {phase_name}")
    print(f"{'='*80}")
    
    results = {"add": [], "modify": []}
    
    # Run Add Tests
    print("\n--- ADD TESTS ---")
    add_inputs = [f"add: {t}" for t in tests_add] + ["end"]
    
    proc = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..", "src", "parser", "chat.py")],
        input="\n".join(add_inputs),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",  # Handle decoding errors
        timeout=120
    )
    
    # Parse output
    output = proc.stdout
    for line in output.split('\n'):
        if "name=" in line and "|" in line:
            # Extract raw output
            raw = line.split(":")[-1].strip()
            results["add"].append(raw)
            print(f"  IN: {tests_add[len(results['add'])-1] if len(results['add']) <= len(tests_add) else '?'}")
            print(f"  OUT: {raw}")

    # Run Modify Tests
    print("\n--- MODIFY TESTS ---")
    for i, (task, change) in enumerate(tests_modify):
        input_json = json.dumps(task)
        mod_input = f"modify: {input_json} | {change}"
        
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "src", "parser", "chat.py")],
            input=f"{mod_input}\nend",
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )
        
        output = proc.stdout
        changed_fields = []
        for line in output.split('\n'):
            line = line.strip()
            if "=" in line and not line.startswith("┌") and not line.startswith("│") and not line.startswith("└"):
                parts = line.split("=")
                if len(parts) >= 2:
                    field = parts[0].strip()
                    val = parts[1].strip()
                    if field in ["difficulty", "importance", "duration", "category", "fixed_start", "fixed_time"]:
                        changed_fields.append(f"{field}={val}")
        
        print(f"  IN: {mod_input[:60]}...")
        print(f"  CHANGED: {', '.join(changed_fields)}")
        results["modify"].append(changed_fields)

    return results

if __name__ == "__main__":
    # Phase 1: Before Specific Fixes
    before = run_test_phase(ADD_TESTS, MODIFY_TESTS, "BEFORE SPECIFIC FIXES")
    
    # Save results for later comparison
    with open("test_results_before.json", "w") as f:
        json.dump(before, f)
    print("\nSaved results to test_results_before.json")
