#!/usr/bin/env python
"""
Test Repair Diagnostics Script
Parses test run failures, isolates stack traces, and generates repair plans.
"""
import os
import sys
import json
import time

def main():
    print("[DIAGNOSTICS] Analysing recent test validation log...")
    
    validation_path = os.path.join("artifacts", "test_validation.json")
    exit_code = 0
    stdout = "No errors detected."
    
    if os.path.exists(validation_path):
        try:
            with open(validation_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                exit_code = data.get("exit_code", 0)
                stdout = data.get("stdout", "")
        except Exception as e:
            stdout = f"Error reading log: {str(e)}"
            exit_code = 1
            
    failures = []
    if exit_code != 0:
        # Extract failed tests or assertion lines from stdout using basic logic
        for line in stdout.splitlines():
            if "FAILED" in line or "AssertionError" in line:
                failures.append(line.strip())
                
    if not failures and exit_code != 0:
        failures.append("Generic test suite execution failure occurred.")
        
    # 1. Output test_failure_summary.json
    failure_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "exit_code": exit_code,
        "failed_test_count": len(failures),
        "failure_traces": failures
    }
    
    os.makedirs("artifacts", exist_ok=True)
    with open(os.path.join("artifacts", "test_failure_summary.json"), "w", encoding="utf-8") as f:
        json.dump(failure_summary, f, indent=2)
        
    # 2. Output repair_plan.json
    repair_plan = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_files": ["tests/test_safe_bash.py"] if failures else [],
        "strategy": "Inspect assertion targets and refine code parameters accordingly.",
        "status": "DRAFT" if failures else "CLEAN"
    }
    with open(os.path.join("artifacts", "repair_plan.json"), "w", encoding="utf-8") as f:
        json.dump(repair_plan, f, indent=2)
        
    # 3. Output repair_history.json
    repair_history = {
        "runs": [
            {
                "run_id": int(time.time()),
                "applied_fixes": [],
                "tests_restored": len(failures) == 0
            }
        ]
    }
    with open(os.path.join("artifacts", "repair_history.json"), "w", encoding="utf-8") as f:
        json.dump(repair_history, f, indent=2)
        
    print(f"[DIAGNOSTICS] Analysis complete. Flagged {len(failures)} failures.")

if __name__ == "__main__":
    main()
