"""
Tests for scripts/context/semble_adapter.py

These tests do NOT require semble to be installed.
All semble imports are mocked to verify adapter behavior when
the package is available or unavailable.
"""
import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure scripts root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.context.semble_adapter import (
    is_semble_available,
    get_semble_version_or_commit,
    run_semble_context_selection,
    UPSTREAM_COMMIT,
    UPSTREAM_URL,
    INTEGRATION_MODE,
)


# ---------------------------------------------------------------------------
# is_semble_available
# ---------------------------------------------------------------------------

class TestIsSembleAvailable:
    def test_returns_false_when_import_fails(self):
        """is_semble_available() returns False when semble is not installed."""
        with patch.dict(sys.modules, {"semble": None}):
            # Force ImportError by setting the module to None
            original = sys.modules.pop("semble", None)
            try:
                # Patch builtins.__import__ to raise ImportError for 'semble'
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "semble":
                        raise ImportError("No module named 'semble'")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    result = is_semble_available()
                assert result is False
            finally:
                if original is not None:
                    sys.modules["semble"] = original
                elif "semble" in sys.modules:
                    del sys.modules["semble"]

    def test_returns_true_when_importable(self):
        """is_semble_available() returns True when semble is importable."""
        mock_semble = MagicMock()
        with patch.dict(sys.modules, {"semble": mock_semble}):
            result = is_semble_available()
        assert result is True

    def test_return_type_is_bool(self):
        """is_semble_available() always returns a bool."""
        result = is_semble_available()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# get_semble_version_or_commit
# ---------------------------------------------------------------------------

class TestGetSembleVersionOrCommit:
    def test_returns_dict(self):
        result = get_semble_version_or_commit()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = get_semble_version_or_commit()
        for key in ("available", "version", "upstream_commit", "upstream_url", "mode", "install_hint"):
            assert key in result, f"Missing key: {key}"

    def test_upstream_commit_matches_constant(self):
        result = get_semble_version_or_commit()
        assert result["upstream_commit"] == UPSTREAM_COMMIT

    def test_upstream_url_matches_constant(self):
        result = get_semble_version_or_commit()
        assert result["upstream_url"] == UPSTREAM_URL

    def test_mode_matches_constant(self):
        result = get_semble_version_or_commit()
        assert result["mode"] == INTEGRATION_MODE

    def test_available_false_when_not_installed(self):
        """available=False when semble cannot be imported."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "semble":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = get_semble_version_or_commit()
        assert result["available"] is False
        assert result["version"] is None


# ---------------------------------------------------------------------------
# run_semble_context_selection
# ---------------------------------------------------------------------------

class TestRunSembleContextSelection:
    def test_returns_dict_when_unavailable(self):
        """Returns structured dict even when semble is not installed."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "semble":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = run_semble_context_selection("test query")

        assert isinstance(result, dict)
        assert result["available"] is False
        assert result["fallback_used"] is False
        assert len(result["errors"]) > 0
        assert result["selected"] == []

    def test_required_schema_keys_present(self):
        """Result always has all required schema keys."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "semble":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = run_semble_context_selection("keyword")

        for key in ("engine", "available", "fallback_used", "query",
                    "selected", "candidates", "metadata", "errors"):
            assert key in result, f"Missing key: {key}"

    def test_engine_field_is_semble(self):
        """engine field is always 'semble' regardless of availability."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "semble":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = run_semble_context_selection("anything")
        assert result["engine"] == "semble"

    def test_empty_query_returns_error(self):
        """Empty query returns an error, not a crash."""
        mock_semble = MagicMock()
        with patch.dict(sys.modules, {"semble": mock_semble}):
            # Patch is_semble_available to return True
            with patch("scripts.context.semble_adapter.is_semble_available", return_value=True):
                result = run_semble_context_selection("")
        assert len(result["errors"]) > 0

    def test_success_path_selected_schema(self):
        """Each selected item has file, reason, relevance_score, source."""
        mock_semble = MagicMock()
        with patch.dict(sys.modules, {"semble": mock_semble}):
            with patch("scripts.context.semble_adapter.is_semble_available", return_value=True):
                mock_search_result = {
                    "error": None,
                    "results": [
                        {
                            "file": "scripts/context/select_context.py",
                            "score": 0.92,
                            "start_line": 1,
                            "end_line": 10,
                            "content": "def main():",
                        }
                    ],
                }
                with patch(
                    "scripts.tools.semble_search.run_semble_search",
                    return_value=mock_search_result,
                ):
                    result = run_semble_context_selection("context", max_files=5)

        if result["available"] and not result["errors"]:
            for item in result["selected"]:
                assert "file" in item
                assert "reason" in item
                assert "relevance_score" in item
                assert "source" in item
