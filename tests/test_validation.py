import sys
import os
import pytest
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.validate.validate_context import validate_context
from scripts.validate.validate_report import validate_report
from scripts.validate.validate_diff import analyze_diff
from scripts.validate.validate_tests import parse_test_metrics

# Backup and restore utilities for selected_context.json
class SandboxContextFile:
    def __init__(self, mock_data):
        self.mock_data = mock_data
        self.context_path = os.path.join("artifacts", "selected_context.json")
        self.backup_path = os.path.join("artifacts", "selected_context.json.bak")
        self.backed_up = False

    def __enter__(self):
        os.makedirs("artifacts", exist_ok=True)
        # Backup if original exists
        if os.path.exists(self.context_path):
            if os.path.exists(self.backup_path):
                os.remove(self.backup_path)
            os.rename(self.context_path, self.backup_path)
            self.backed_up = True
            
        # Write mock data
        with open(self.context_path, "w", encoding="utf-8") as f:
            json.dump(self.mock_data, f, indent=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.context_path):
            os.remove(self.context_path)
        # Restore backup
        if self.backed_up and os.path.exists(self.backup_path):
            os.rename(self.backup_path, self.context_path)

def test_validate_context_success():
    """Test context validator with perfectly valid files and reasons."""
    mock_data = [
        {"file": "scripts/tools/safe_bash.py", "reason": "Necessary file for running bash commands securely."},
        {"file": "tests/test_safe_bash.py", "reason": "Pytest verification file for testing safe_bash implementation."}
    ]
    
    with SandboxContextFile(mock_data):
        report = validate_context()
        assert report["passed"] is True
        assert report["verdict"] == "PASS"
        assert report["total_files"] == 2
        assert len(report["issues"]) == 0

def test_validate_context_failures():
    """Test context validation rules for limits, empty rationale, and forbidden patterns."""
    mock_data = [
        {"file": "node_modules/lodash/index.js", "reason": "Trivial"}, # Excluded folder and rationale too short
        {"file": "scripts/safe.py", "reason": ""} # Rationale empty
    ]
    
    with SandboxContextFile(mock_data):
        report = validate_context()
        assert report["passed"] is False
        assert report["verdict"] == "FAIL"
        
        issues_str = "".join(report["issues"])
        assert "FORBIDDEN_FILE_PATTERN" in issues_str
        assert "MISSING_RATIONALE" in issues_str

def test_validate_report_audit():
    """Test report validator for headers, verdicts, and lazy phrasing."""
    valid_report = """# Task Execution Report
## Metadata
* **Verdict**: PASS
* **Timestamp**: 2026-05-30 23:00:00

## Security Check Status
* **Status**: PASS

## Git Diff Analysis
* **Status**: PASS

## Test Run Results
* **Exit Code**: 0
"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md", encoding="utf-8") as tmp:
        tmp.write(valid_report)
        tmp_name = tmp.name
        
    try:
        # 1. Valid report should pass
        report = validate_report(tmp_name)
        assert report["passed"] is True
        
        # 2. Add lazy phrase
        lazy_report = valid_report + "\nIt's all good, should be fine and probably fixed now!"
        with open(tmp_name, "w", encoding="utf-8") as f:
            f.write(lazy_report)
            
        report_lazy = validate_report(tmp_name)
        assert report_lazy["passed"] is False
        issues_str = "".join(report_lazy["issues"])
        assert "LAZY_PHRASE_DETECTED" in issues_str
        
        # 3. Invalid verdict
        bad_verdict_report = valid_report.replace("**Verdict**: PASS", "**Verdict**: EXCELLENT")
        with open(tmp_name, "w", encoding="utf-8") as f:
            f.write(bad_verdict_report)
            
        report_verdict = validate_report(tmp_name)
        assert report_verdict["passed"] is False
        assert "ILLEGAL_VERDICT" in "".join(report_verdict["issues"])
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def test_validate_diff_enhancements():
    """Test enhanced diff validation detecting secrets and unrelated edits."""
    mock_selected = ["scripts/allowed.py"]
    
    # 1. Diff with unrelated edit
    unrelated_diff = """diff --git a/scripts/unrelated.py b/scripts/unrelated.py
index a53c7d1..f356d4b 100644
--- a/scripts/unrelated.py
+++ b/scripts/unrelated.py
@@ -1 +1,2 @@
+print("unrelated edit")
"""
    res = analyze_diff(unrelated_diff, max_files=10, suspicious_exts=[], selected_files=mock_selected)
    assert res["verdict"] == "WRONG_FILE_EDIT"
    assert res["passed"] is False
    assert "scripts/unrelated.py" in res["unrelated_edits"]
    
    # 2. Diff with secrets
    secrets_diff = """diff --git a/scripts/allowed.py b/scripts/allowed.py
index a53c7d1..f356d4b 100644
--- a/scripts/allowed.py
+++ b/scripts/allowed.py
@@ -1 +1,2 @@
+API_KEY = "sk-ant-sid1234567890abcdefghijklmnopqrstuvwxyz"
"""
    res_sec = analyze_diff(secrets_diff, max_files=10, suspicious_exts=[], selected_files=mock_selected)
    assert res_sec["verdict"] == "SECRET_RISK"
    assert res_sec["passed"] is False

def test_parse_test_metrics():
    """Test pytest output metrics regex parser."""
    # 1. Multiple types
    stdout_multi = "================ 2 failed, 15 passed, 1 skipped in 0.62s ================"
    metrics = parse_test_metrics(stdout_multi)
    assert metrics["passed"] == 15
    assert metrics["failed"] == 2
    assert metrics["skipped"] == 1
    assert metrics["total"] == 18
    
    # 2. Single passing
    stdout_pass = "================ 17 passed in 0.62s ================"
    metrics_pass = parse_test_metrics(stdout_pass)
    assert metrics_pass["passed"] == 17
    assert metrics_pass["failed"] == 0
    assert metrics_pass["skipped"] == 0
    assert metrics_pass["total"] == 17
