#!/usr/bin/env python
"""
Context Validation Scanner
Verifies that loaded context files do not violate size, directory, or safety exclusions.
"""
import os
import sys
import re
import json

def load_context_config():
    """Load settings from configs/context.yaml."""
    cfg_path = os.path.join("configs", "context.yaml")
    max_files = 20
    excludes = ["node_modules", "__pycache__", ".git", "build", "dist", ".pytest_cache"]
    
    if not os.path.exists(cfg_path):
        return max_files, excludes
        
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        max_match = re.search(r"max_files_selected:\s*(\d+)", content)
        if max_match:
            max_files = int(max_match.group(1))
            
        exclude_section = re.search(r"exclude_patterns:\s*\n((?:\s*-\s*\"[^\"]+\"\s*\n?)+)", content)
        if exclude_section:
            patterns = re.findall(r'-\s*"([^"]+)"', exclude_section.group(1))
            if patterns:
                excludes = [p.replace("**/", "").replace("/**", "") for p in patterns]
                
        return max_files, excludes
    except Exception:
        return max_files, excludes

def validate_context():
    """Scan and validate selected_context.json against rules."""
    context_path = os.path.join("artifacts", "selected_context.json")
    
    if not os.path.exists(context_path):
        return {
            "verdict": "FAIL",
            "passed": False,
            "message": "Missing selected_context.json. Context selection has not been completed.",
            "total_files": 0,
            "issues": ["MISSING_CONTEXT_DATA"]
        }
        
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            selected_files = json.load(f)
    except Exception as e:
        return {
            "verdict": "FAIL",
            "passed": False,
            "message": f"Failed to load selected_context.json: {str(e)}",
            "total_files": 0,
            "issues": ["MALFORMED_JSON"]
        }
        
    max_files, excludes = load_context_config()
    issues = []
    
    # 1. Total files limit check
    total_files = len(selected_files)
    if total_files > max_files:
        issues.append(f"TOTAL_FILES_EXCEEDED (Selected: {total_files}, Limit: {max_files})")
        
    # 2. File audit checks
    for idx, item in enumerate(selected_files, 1):
        filename = item.get("file", "")
        reason = item.get("reason", "").strip()
        
        # Check exclusion matches
        matched_exclude = None
        for pattern in excludes:
            if pattern in filename:
                matched_exclude = pattern
                break
                
        if matched_exclude:
            issues.append(f"FORBIDDEN_FILE_PATTERN: '{filename}' matched exclude pattern '{matched_exclude}'")
            
        # Check for empty rationales
        if not reason or len(reason) < 10:
            issues.append(f"MISSING_RATIONALE: File '{filename}' has an empty or too short reason.")
            
    passed = len(issues) == 0
    verdict = "PASS" if passed else "FAIL"
    message = "Context selection matches all constraints and limits." if passed else f"Context validation warnings: {', '.join(issues)}"
    
    return {
        "verdict": verdict,
        "passed": passed,
        "message": message,
        "total_files": total_files,
        "limit_files": max_files,
        "issues": issues,
        "checked_files": [i.get("file") for i in selected_files]
    }

def main():
    report = validate_context()
    
    # Save report
    os.makedirs("artifacts", exist_ok=True)
    report_path = os.path.join("artifacts", "context_validation.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"[{report['verdict']}] Context Selection Validation")
    print(f"Message: {report['message']}")
    
    sys.exit(0 if report["passed"] else 1)

if __name__ == "__main__":
    main()
