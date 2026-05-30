import sys
import os
import pytest
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.context.build_index import parse_python_symbols
from scripts.context.compress_context import strip_python_comments_and_docstrings
from scripts.context.summarize_repo import calculate_footprint

def test_ast_python_symbols_parsing():
    """Verify AST symbol extraction on structured Python strings."""
    mock_code = """
import os
from sys import exit

class SampleClass:
    def __init__(self):
        self.val = 1
        
    def execute_task(self):
        return "done"

def top_level_fn():
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py", encoding="utf-8") as tmp:
        tmp.write(mock_code)
        tmp_name = tmp.name
        
    try:
        symbols = parse_python_symbols(tmp_name)
        assert "classes" in symbols
        assert len(symbols["classes"]) == 1
        assert symbols["classes"][0]["name"] == "SampleClass"
        assert "execute_task" in symbols["classes"][0]["methods"]
        
        assert "functions" in symbols
        # Depending on traversal, top_level_fn is found
        fn_names = [f["name"] for f in symbols["functions"]]
        assert "top_level_fn" in fn_names
        
        assert "imports" in symbols
        assert "os" in symbols["imports"]
        assert "sys" in symbols["imports"]
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def test_comment_and_docstring_compactor():
    """Verify strip_python_comments_and_docstrings strips comments and whitespaces."""
    mock_code = '''
def calculate():
    """This is a multi-line docstring
    that should be compacted.
    """
    # This is a single-line comment to strip
    val = 42 # inline comment
    return val
'''
    # 1. Medium compact level (docstrings & comments stripped, single blank lines kept)
    med_compact = strip_python_comments_and_docstrings(mock_code, "medium")
    assert "docstring" not in med_compact
    assert "single-line comment" not in med_compact
    assert "val = 42" in med_compact
    assert "inline comment" not in med_compact
    
    # 2. High compact level (all comments and consecutive blank lines stripped)
    high_compact = strip_python_comments_and_docstrings(mock_code, "high")
    assert "\n\n" not in high_compact
    assert "docstring" not in high_compact

def test_footprint_summarizer():
    """Verify calculate_footprint successfully executes and writes structure summary."""
    # Run calculate_footprint and verify it writes artifacts/repo_structure_summary.json
    try:
        success = calculate_footprint()
        assert success is True
        
        summary_path = os.path.join("artifacts", "repo_structure_summary.json")
        assert os.path.exists(summary_path)
        
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "footprint" in data
            assert data["footprint"]["total_files"] > 0
            assert "total_size_bytes" in data["footprint"]
    finally:
        pass
