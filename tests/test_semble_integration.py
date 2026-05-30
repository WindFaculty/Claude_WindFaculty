import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.context.select_context import load_semble_config
from scripts.tools.semble_search import check_semble_available, run_semble_search

def test_load_semble_config():
    """Verify that load_semble_config correctly parses Semble settings from configs/context.yaml."""
    enable, top_k = load_semble_config()
    assert isinstance(enable, bool)
    assert isinstance(top_k, int)
    assert enable is True
    assert top_k == 10

def test_check_semble_available():
    """Verify that check_semble_available handles missing or available package correctly."""
    passed, msg = check_semble_available()
    assert isinstance(passed, bool)
    assert isinstance(msg, str)

def test_run_semble_search_not_installed():
    """Verify that run_semble_search handles missing packages gracefully."""
    with patch('scripts.tools.semble_search.check_semble_available') as mock_check:
        mock_check.return_value = (False, "semble package is not installed.")
        res = run_semble_search("test query")
        assert res["error"] == "semble package is not installed."
        assert len(res["results"]) == 0

def test_run_semble_search_success():
    """Verify that run_semble_search returns properly formatted output when Semble succeeds."""
    mock_chunk = MagicMock()
    mock_chunk.file_path = "scripts/bootstrap/setup.ps1"
    mock_chunk.content = "Write-Host"
    mock_chunk.start_line = 1
    mock_chunk.end_line = 5

    mock_result = MagicMock()
    mock_result.chunk = mock_chunk
    mock_result.score = 0.85

    with patch('scripts.tools.semble_search.check_semble_available') as mock_check:
        mock_check.return_value = (True, "Mock available")
        
        # Mock sys.modules to mock semble import
        sys.modules['semble'] = MagicMock()
        
        with patch('semble.SembleIndex.from_path') as mock_from_path:
            mock_index = MagicMock()
            mock_index.search.return_value = [mock_result]
            mock_from_path.return_value = mock_index
            
            res = run_semble_search("test query", top_k=5, path=".")
            assert res["error"] is None
            assert len(res["results"]) == 1
            assert res["results"][0]["file"] == "scripts/bootstrap/setup.ps1"
            assert res["results"][0]["score"] == 0.85
            assert res["results"][0]["content"] == "Write-Host"
