#!/usr/bin/env python
"""
Unified Execution Report Generator
Aggregates intake logs, diff reviews, and test runs to create final markdown reports.
"""
import os
import json
import time

def read_artifact_json(filename):
    path = os.path.join("artifacts", filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def main():
    print("[REPORTS] Compiling unified execution report...")
    
    # Read available artifacts
    diff_report = read_artifact_json("diff_validation.json") or {"verdict": "UNKNOWN", "changed_files": [], "message": "No diff report found."}
    test_report = read_artifact_json("test_validation.json") or {"exit_code": -1, "stdout": "No test run recorded."}
    security_report = read_artifact_json("security_validation.json") or {"passed": True}
    
    # Determine final verdict
    passed = security_report.get("passed", True) and test_report.get("exit_code", 1) == 0
    verdict = "PASS" if passed else "FAIL"
    
    # Build report path
    os.makedirs("reports", exist_ok=True)
    report_filename = f"execution_report_{int(time.time())}.md"
    report_path = os.path.join("reports", report_filename)
    
    content = f"""# Task Execution Report

## Metadata
* **Verdict**: {verdict}
* **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}
* **Environment**: Claude_WindFaculty Environment

## Security Check Status
* **Status**: {"PASS" if security_report.get("passed", True) else "FAIL - Key Exposed!"}

## Git Diff Analysis
* **Status**: {diff_report.get("verdict", "UNKNOWN")}
* **Changed Files**: {", ".join(diff_report.get("changed_files", [])) or "None"}
* **Details**: {diff_report.get("message", "")}

## Test Run Results
* **Exit Code**: {test_report.get("exit_code", -1)}
* **Execution Summary**:
```text
{test_report.get("stdout", "")[:1000]}
```

---
*Report compiled automatically by Claude_WindFaculty Report Writer.*
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"[REPORTS] Created report at {report_path}")

if __name__ == "__main__":
    main()
