"""
    VM.AI Parser — Full Test Suite Runner
    Runs all 4 test scripts independently.
    Run: python tests/test_llm_full.py
"""

import sys
import os
import subprocess
import time

SCRIPTS = ["test_core.py", "test_generator.py", "test_add.py", "test_modify.py"]
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

results = {}
total_passed = 0
total_failed = 0

print("="*80)
print("  VM.AI FULL TEST SUITE")
print("="*80)

for script in SCRIPTS:
    path = os.path.join(TESTS_DIR, script)
    name = script.replace("test_", "").replace(".py", "").upper()
    print(f"\n{'─'*80}")
    print(f"  RUNNING: {script}")
    print(f"{'─'*80}")

    start = time.time()
    proc = subprocess.run([PYTHON, path], text=True, capture_output=True, encoding="utf-8", timeout=600)
    elapsed = time.time() - start

    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr[-500:])

    passed = proc.returncode == 0
    results[script] = passed

    # Parse passed/total from output
    for line in proc.stdout.split("\n"):
        if "RESULTS:" in line:
            try:
                parts = line.split(":")[1].strip().split("/")[0]
                total = line.split("/")[1].split(" ")[0]
                total_passed += int(parts)
                total_failed += int(total) - int(parts)
            except:
                pass

print(f"\n{'='*80}")
print("  FINAL SUMMARY")
print("="*80)

for script, passed in results.items():
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {script}")

all_passed = all(results.values())
total = total_passed + total_failed
pct = (100*total_passed//total) if total > 0 else 0
print(f"\n{'='*80}")
print(f"  TOTAL: {total_passed}/{total} passed ({pct}%)")
print(f"{'='*80}")

if all_passed:
    print("\n  ALL TESTS PASSED")
else:
    print(f"\n  {len([s for s, p in results.items() if not p])} TEST SUITE(S) FAILED")

sys.exit(0 if all_passed else 1)
