"""
    VM-AI - Automated Test Suite for Chat Interface
    Runs Add and Modify tests against the model, captures outputs.
    Run: python tests/test_chat_suite.py

    Requires: finetuned_parser model in models/
"""

import sys
import os
import subprocess
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parser'))

# ── Test Cases ──────────────────────────────────────────────────────────────

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
    # (existing_task_dict, change_instruction)
    ({"name": "gym", "fixed_time": True, "fixed_start": "06:00", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "recurrent": False}, "move to 7am"),
    ({"name": "workout", "duration": 45, "category": "fitness", "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "make it harder"),
    ({"name": "client call", "importance": 0.5, "duration": 30, "category": "work", "difficulty": 0.3, "fixed_time": False, "recurrent": False}, "make it urgent"),
    ({"name": "yoga", "category": "work", "duration": 60, "difficulty": 0.35, "importance": 0.5, "fixed_time": False, "recurrent": False}, "categorize it as fitness"),
    ({"name": "meeting", "fixed_time": True, "fixed_start": "14:00", "duration": 30, "category": "work", "difficulty": 0.2, "importance": 0.6, "recurrent": False}, "make it 1 hour"),
]


def run_add_tests(tests):
    """Run add tests via chat.py subprocess."""
    chat_path = os.path.join(os.path.dirname(__file__), "..", "src", "parser", "chat.py")
    inputs = [f"add: {t}" for t in tests] + ["end"]

    proc = subprocess.run(
        [sys.executable, chat_path],
        input="\n".join(inputs),
        text=True,
        capture_output=True,
        timeout=300,
    )

    results = []
    for line in proc.stdout.split("\n"):
        if "name=" in line and "|" in line:
            raw = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
            if raw and len(results) < len(tests):
                results.append({"input": tests[len(results)], "raw": raw})

    return results


def run_modify_tests(tests):
    """Run modify tests via chat.py subprocess.
    
    New format: modify json → paste JSON → then change prompt.
    """
    chat_path = os.path.join(os.path.dirname(__file__), "..", "src", "parser", "chat.py")
    results = []

    for task, change in tests:
        # Use modify json flow
        inputs = ["modify json", json.dumps(task), change, "end"]

        proc = subprocess.run(
            [sys.executable, chat_path],
            input="\n".join(inputs),
            text=True,
            capture_output=True,
            timeout=60,
        )

        changed = []
        for line in proc.stdout.split("\n"):
            line = line.strip()
            if "=" in line and not any(line.startswith(p) for p in ["┌", "│", "└", "EXP", "PASS", "FAIL"]):
                parts = line.split("=")
                if len(parts) >= 2:
                    field = parts[0].strip()
                    val = parts[1].strip().split("[")[0].strip()
                    if field and val:
                        changed.append(f"{field}={val}")

        results.append({"input": change, "task": task, "changed": changed})

    return results


if __name__ == "__main__":
    print("=" * 80)
    print("  CHAT INTERFACE TEST SUITE")
    print("=" * 80)

    # ── Add Tests ───────────────────────────────────────────────────────
    print("\n--- ADD TESTS ---")
    add_results = run_add_tests(ADD_TESTS)
    for r in add_results:
        print(f"  IN:  {r['input']}")
        print(f"  OUT: {r['raw']}")

    # ── Modify Tests ────────────────────────────────────────────────────
    print("\n--- MODIFY TESTS ---")
    mod_results = run_modify_tests(MODIFY_TESTS)
    for r in mod_results:
        print(f"  IN:  {r['input']}")
        print(f"  TASK: {r['task'].get('name', '?')}")
        print(f"  CHANGED: {', '.join(r['changed']) if r['changed'] else 'none'}")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"  Add tests: {len(add_results)} run")
    print(f"  Modify tests: {len(mod_results)} run")
    print(f"{'=' * 80}")
