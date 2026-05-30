import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.validate.validate_diff import (
    analyze_diff,
    parse_changed_files
)

def test_validate_no_diff():
    # Test empty diff text
    report = analyze_diff("", max_files=5, suspicious_exts=[".pyc"])
    assert report["verdict"] == "NO_DIFF"
    assert report["passed"] is False
    assert "No active modifications found" in report["message"]

def test_validate_normal_diff():
    sample_diff = """diff --git a/scripts/tools/safe_bash.py b/scripts/tools/safe_bash.py
index a1b2c3d..e5f6g7h 100644
--- a/scripts/tools/safe_bash.py
+++ b/scripts/tools/safe_bash.py
@@ -10,3 +10,4 @@
+# added some safe commands here
"""
    files = parse_changed_files(sample_diff)
    assert "scripts/tools/safe_bash.py" in files
    
    report = analyze_diff(sample_diff, max_files=5, suspicious_exts=[".pyc"])
    assert report["verdict"] == "PASS"
    assert report["passed"] is True

def test_validate_too_broad_diff():
    sample_diff = """diff --git a/file1.py b/file1.py
diff --git a/file2.py b/file2.py
diff --git a/file3.py b/file3.py
"""
    report = analyze_diff(sample_diff, max_files=2, suspicious_exts=[".pyc"])
    assert report["verdict"] == "TOO_BROAD_DIFF"
    assert report["passed"] is False
    assert "TOO_BROAD_DIFF" in report["issues"]

def test_validate_suspicious_extension():
    sample_diff = """diff --git a/compiled.pyc b/compiled.pyc
"""
    report = analyze_diff(sample_diff, max_files=5, suspicious_exts=[".pyc"])
    assert report["verdict"] == "SUSPICIOUS_FILES"
    assert report["passed"] is False
    assert "SUSPICIOUS_FILES" in report["issues"]
    assert "compiled.pyc" in report["suspicious_files"]
