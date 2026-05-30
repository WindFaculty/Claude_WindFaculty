#!/usr/bin/env python
"""
Diff Validation Script
Validates active workspace diffs for size, suspicious files, and safety rules.
"""
import sys
import os
import subprocess
import re
import json

def load_validation_config():
    """Load settings from configs/validation.yaml."""
    cfg_path = os.path.join("configs", "validation.yaml")
    max_files = 10
    suspicious_exts = [".pyc", ".o", ".obj", ".dll", ".exe", ".zip", ".tar.gz"]
    
    if not os.path.exists(cfg_path):
        return max_files, suspicious_exts
        
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Simple extraction
        match_max = re.search(r"max_files_modified:\s*(\d+)", content)
        if match_max:
            max_files = int(match_max.group(1))
            
        exts_match = re.search(r"suspicious_extensions:\s*\n((?:\s*-\s*\"[^\"]+\"\s*\n?)+)", content)
        if exts_match:
            suspicious_exts = re.findall(r'-\s*"([^"]+)"', exts_match.group(1))
            
        return max_files, suspicious_exts
    except Exception:
        return max_files, suspicious_exts

def get_git_diff():
    """Get raw active git diff (staged + unstaged)."""
    try:
        # Check both cached and uncached diffs
        res = subprocess.run(["git", "diff", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if res.returncode == 0:
            return res.stdout
        
        # Fallback if HEAD does not exist (new repo with no commits)
        res_staged = subprocess.run(["git", "diff", "--cached"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        res_unstaged = subprocess.run(["git", "diff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        return (res_staged.stdout or "") + (res_unstaged.stdout or "")
    except Exception:
        return ""

def parse_changed_files(diff_text):
    """Extract list of changed files from standard git diff content."""
    files = set()
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            # Parse diff --git a/file b/file
            parts = re.findall(r"b/([^\s\n]+)", line)
            if parts:
                files.add(parts[-1])
    return list(files)

def analyze_diff(diff_text, max_files, suspicious_exts):
    """Analyze diff content and return classification verdicts."""
    if not diff_text.strip():
        return {
            "verdict": "NO_DIFF",
            "passed": False,
            "message": "No active modifications found in git diff.",
            "changed_files": [],
            "issues": ["NO_DIFF"]
        }
        
    changed_files = parse_changed_files(diff_text)
    issues = []
    
    # 1. Broad diff check
    if len(changed_files) > max_files:
        issues.append("TOO_BROAD_DIFF")
        
    # 2. Suspicious file check
    suspicious_found = []
    for file in changed_files:
        _, ext = os.path.splitext(file)
        if ext in suspicious_exts:
            suspicious_found.append(file)
            
    if suspicious_found:
        issues.append("SUSPICIOUS_FILES")
        
    # Determine overall verdict
    if not issues:
        verdict = "PASS"
        passed = True
        message = "Diff matches all validation limits and safety rules."
    else:
        verdict = "FAIL"
        passed = False
        message = f"Validation warnings encountered: {', '.join(issues)}"
        
    return {
        "verdict": verdict,
        "passed": passed,
        "message": message,
        "changed_files": changed_files,
        "suspicious_files": suspicious_found,
        "issues": issues
    }

def main():
    max_files, suspicious_exts = load_validation_config()
    
    # Fetch actual diff
    diff_text = get_git_diff()
    
    # Run analysis
    report = analyze_diff(diff_text, max_files, suspicious_exts)
    
    # Write output to artifacts
    os.makedirs("artifacts", exist_ok=True)
    with open(os.path.join("artifacts", "diff_validation.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    with open(os.path.join("artifacts", "diff_review.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    patch_acceptance = {
        "accepted": report["passed"] or report["verdict"] == "NO_DIFF",
        "verdict": report["verdict"],
        "message": report["message"]
    }
    with open(os.path.join("artifacts", "patch_acceptance.json"), "w", encoding="utf-8") as f:
        json.dump(patch_acceptance, f, indent=2)
        
    print(f"[{report['verdict']}] Diff Validation Report")
    print(f"Message: {report['message']}")
    print(f"Files Modified ({len(report['changed_files'])}): {', '.join(report['changed_files'])}")
    if report.get("suspicious_files"):
        print(f"WARNING: Suspicious files flagged: {', '.join(report['suspicious_files'])}")
        
    # Exit with 0 if passed, or exit code 0/1 depending on strictness
    # Usually we don't want to break the pipeline if NO_DIFF is just a warning, but for absolute safety return code 0 or 1
    sys.exit(0 if report["passed"] or report["verdict"] == "NO_DIFF" else 1)

if __name__ == "__main__":
    main()
