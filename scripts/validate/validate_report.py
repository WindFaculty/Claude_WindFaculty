#!/usr/bin/env python
"""
Report Integrity Validator
Checks final task reports for layout completeness, valid verdicts, and blocks lazy non-evidence phrasing.
"""
import os
import sys
import re
import json

REQUIRED_SECTIONS = [
    (r"#\s+Task(?:\s+Execution)?\s+Report", "Report Main Title"),
    (r"##\s+Metadata", "Metadata Section"),
    (r"##\s+Security(?:\s+Check)?(?:\s+Status)?", "Security Section"),
    (r"##\s+Git\s+Diff(?:\s+Analysis)?", "Git Diff Section"),
    (r"##\s+Test\s+Run(?:\s+Results)?", "Test Run Section")
]

LEGAL_VERDICTS = ["PASS", "PASS_WITH_WARNINGS", "FAIL", "BLOCKED", "SKIPPED"]

LAZY_PHRASES = [
    ("all good", "Lazy phrase 'all good' provides no technical verification."),
    ("done", "Lazy term 'done' without evidence is non-committal."),
    ("should be fine", "Lazy assumption 'should be fine' does not constitute proof."),
    ("probably fixed", "Lazy statement 'probably fixed' indicates lack of test validation.")
]

def find_latest_report():
    """Locate the most recently modified markdown file in reports/."""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        return None
        
    md_files = []
    for file in os.listdir(reports_dir):
        if file.endswith(".md") and (file.startswith("execution_report") or file.startswith("final")):
            path = os.path.join(reports_dir, file)
            if os.path.isfile(path):
                md_files.append((path, os.path.getmtime(path)))
                
    if not md_files:
        return None
        
    # Sort by modification time descending
    md_files.sort(key=lambda x: x[1], reverse=True)
    return md_files[0][0]

def validate_report(filepath):
    """Audits the markdown report content for rules."""
    if not filepath or not os.path.exists(filepath):
        return {
            "verdict": "FAIL",
            "passed": False,
            "message": "No compiled task report found in reports/.",
            "issues": ["MISSING_REPORT"]
        }
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {
            "verdict": "FAIL",
            "passed": False,
            "message": f"Failed reading report file: {str(e)}",
            "issues": ["READ_ERROR"]
        }
        
    issues = []
    
    # 1. Structural Auditing
    for pattern, name in REQUIRED_SECTIONS:
        if not re.search(pattern, content, re.IGNORECASE):
            issues.append(f"MISSING_SECTION: Report is missing the '{name}' section.")
            
    # 2. Verdict Auditing
    # Find something like Verdict: PASS or **Verdict**: PASS
    verdict_match = re.search(r"verdict\s*[:*]*\s*([a-zA-Z_]+)", content, re.IGNORECASE)
    if verdict_match:
        verdict_str = verdict_match.group(1).upper()
        if verdict_str not in LEGAL_VERDICTS:
            issues.append(f"ILLEGAL_VERDICT: Found verdict '{verdict_str}', which is not in {LEGAL_VERDICTS}.")
    else:
        issues.append("MISSING_VERDICT: No clear final verdict was declared in report metadata.")
        
    # 3. Phrasing Auditing (check for lazy phrases outside code/quoted blocks)
    # Strip fenced code blocks first to avoid false-positives
    sanitized_content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    
    for phrase, warning in LAZY_PHRASES:
        if phrase in sanitized_content.lower():
            # Check if it's used lazy or in normal context - let's flag as a warning/issue
            issues.append(f"LAZY_PHRASE_DETECTED: '{phrase}'. {warning}")
            
    passed = len(issues) == 0
    verdict = "PASS" if passed else "FAIL"
    message = "Report integrity matches all completeness standards." if passed else f"Report integrity audit warnings: {', '.join(issues)}"
    
    return {
        "verdict": verdict,
        "passed": passed,
        "message": message,
        "report_file": filepath,
        "issues": issues
    }

def main():
    report_file = find_latest_report()
    report = validate_report(report_file)
    
    # Save validation report
    os.makedirs("artifacts", exist_ok=True)
    report_path = os.path.join("artifacts", "report_validation.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"[{report['verdict']}] Final Report Integrity Audit")
    print(f"Audited file: {report.get('report_file', 'None')}")
    print(f"Message: {report['message']}")
    
    sys.exit(0 if report["passed"] else 1)

if __name__ == "__main__":
    main()
