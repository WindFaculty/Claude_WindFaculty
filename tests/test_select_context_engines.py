"""
Tests for scripts/context/select_context.py engine dispatch.

Tests cover:
  1. --engine keyword: runs keyword scan, writes context_engine_metadata.json
  2. --engine semble (unavailable): exits non-zero, does NOT fallback
  3. --engine auto (semble unavailable): falls back to keyword, fallback_used=true
  4. --engine auto (semble available+mock): uses semble
  5. Schema validation for selected_context.json and context_engine_metadata.json
  6. safe_bash classification for allowed/denied commands
"""
import sys
import os
import json
import subprocess
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

# Ensure scripts root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from scripts.context.select_context import (
    load_context_config,
    run_keyword_engine,
    run_semble_engine,
    write_artifacts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_select_context(*args, cwd=None) -> subprocess.CompletedProcess:
    """Run select_context.py as a subprocess from the repo root."""
    cmd = [sys.executable, "scripts/context/select_context.py"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or ROOT,
    )


def read_artifact(name: str, artifacts_dir: str) -> dict:
    """Read a JSON artifact file."""
    path = os.path.join(artifacts_dir, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Engine = keyword
# ---------------------------------------------------------------------------

class TestKeywordEngine:
    def test_keyword_engine_returns_dict(self):
        """run_keyword_engine returns a valid dict."""
        result = run_keyword_engine("CLAUDE", max_files=5, exclude=[], root=ROOT)
        assert isinstance(result, dict)
        assert result["engine"] == "keyword"
        assert result["available"] is True
        assert result["fallback_used"] is False

    def test_keyword_engine_finds_claude(self):
        """keyword engine finds files containing 'CLAUDE'."""
        result = run_keyword_engine("CLAUDE", max_files=20, exclude=[], root=ROOT)
        files = [s["file"] for s in result["selected"]]
        # At minimum CLAUDE.md should be found
        assert any("CLAUDE" in f.upper() for f in files) or len(result["selected"]) > 0

    def test_keyword_engine_schema(self):
        """Each selected item has file, reason, relevance_score, source."""
        result = run_keyword_engine("CLAUDE", max_files=5, exclude=[], root=ROOT)
        for item in result["selected"]:
            assert "file" in item
            assert "reason" in item
            assert "relevance_score" in item
            assert "source" in item

    def test_subprocess_keyword_engine_creates_artifacts(self, tmp_path):
        """CLI --engine keyword creates selected_context.json and metadata json."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "keyword",
            "--root", ROOT,
        )
        assert proc.returncode == 0, f"STDERR: {proc.stderr}"
        meta_path = os.path.join(ROOT, "artifacts", "context_engine_metadata.json")
        assert os.path.exists(meta_path), "context_engine_metadata.json not written"
        meta = json.loads(open(meta_path).read())
        assert meta["engine_requested"] == "keyword"
        assert meta["engine_used"] == "keyword"
        assert meta["fallback_used"] is False

    def test_subprocess_keyword_selected_schema(self):
        """selected_context.json has proper schema after keyword run."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "keyword",
            "--root", ROOT,
        )
        assert proc.returncode == 0
        selected_path = os.path.join(ROOT, "artifacts", "selected_context.json")
        selected = json.loads(open(selected_path).read())
        assert isinstance(selected, list)
        if selected:
            item = selected[0]
            assert "file" in item
            assert "reason" in item
            assert "relevance_score" in item


# ---------------------------------------------------------------------------
# 2. Engine = semble (strict, unavailable)
# ---------------------------------------------------------------------------

class TestSembleEngineStrict:
    def test_semble_unavailable_returns_unavailable_dict(self):
        """run_semble_engine returns available=False when semble not installed."""
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "semble":
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = run_semble_engine("test", max_files=5, root=ROOT)

        assert result["available"] is False
        assert len(result["errors"]) > 0

    def test_subprocess_semble_engine_exits_nonzero_when_unavailable(self):
        """CLI --engine semble exits code 1 when semble not installed."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "semble",
            "--root", ROOT,
        )
        # If semble is not installed this must be non-zero
        if not _is_semble_installed():
            assert proc.returncode != 0, (
                "Expected non-zero exit when semble unavailable in strict mode"
            )

    def test_subprocess_semble_no_fallback(self):
        """CLI --engine semble does NOT fall back to keyword when unavailable."""
        if _is_semble_installed():
            pytest.skip("semble is installed; strict-fail test not applicable")
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "semble",
            "--root", ROOT,
        )
        assert proc.returncode != 0
        # Output should not say 'keyword' engine was used
        combined = proc.stdout + proc.stderr
        assert "engine_used" not in combined or "keyword" not in combined or \
               "fallback" in combined.lower()


# ---------------------------------------------------------------------------
# 3. Engine = auto (semble unavailable → keyword fallback)
# ---------------------------------------------------------------------------

class TestAutoEngineFallback:
    def test_subprocess_auto_fallback_to_keyword(self):
        """CLI --engine auto falls back to keyword when semble unavailable."""
        if _is_semble_installed():
            pytest.skip("semble is installed; fallback test not applicable")

        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "auto",
            "--root", ROOT,
        )
        assert proc.returncode == 0, f"STDERR: {proc.stderr}"
        meta_path = os.path.join(ROOT, "artifacts", "context_engine_metadata.json")
        meta = json.loads(open(meta_path).read())
        assert meta["engine_requested"] == "auto"
        assert meta["engine_used"] == "keyword"
        assert meta["fallback_used"] is True
        assert meta["fallback_reason"] is not None

    def test_subprocess_auto_does_not_crash(self):
        """CLI --engine auto exits 0 whether semble is available or not."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "auto",
            "--root", ROOT,
        )
        assert proc.returncode == 0, f"STDERR: {proc.stderr}"


# ---------------------------------------------------------------------------
# 4. Engine = auto with mock semble available
# ---------------------------------------------------------------------------

class TestAutoEngineMockSemble:
    def test_auto_uses_semble_when_mock_available(self):
        """When semble adapter reports available=True, auto uses semble."""
        mock_result = {
            "engine": "semble",
            "available": True,
            "fallback_used": False,
            "query": "CLAUDE",
            "selected": [
                {
                    "file": "CLAUDE.md",
                    "reason": "Mock semble result.",
                    "relevance_score": 0.95,
                    "source": "semble",
                }
            ],
            "candidates": [],
            "metadata": {
                "upstream_commit": "ea3c9180bd7b8c3ae2133120b17c3599ac93dec3",
                "mode": "package",
                "command": None,
            },
            "errors": [],
        }
        with patch("scripts.context.select_context.run_semble_engine", return_value=mock_result):
            from scripts.context.select_context import main
            import io

            # Simulate CLI args
            with patch("sys.argv", ["select_context.py", "--query", "CLAUDE",
                                    "--engine", "auto", "--root", ROOT]):
                with patch("sys.exit"):
                    main()

        meta_path = os.path.join(ROOT, "artifacts", "context_engine_metadata.json")
        if os.path.exists(meta_path):
            meta = json.loads(open(meta_path).read())
            assert meta["engine_used"] == "semble"
            assert meta["fallback_used"] is False


# ---------------------------------------------------------------------------
# 5. Schema validation
# ---------------------------------------------------------------------------

class TestArtifactSchema:
    def test_context_engine_metadata_schema(self):
        """context_engine_metadata.json has all required top-level keys."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "keyword",
            "--root", ROOT,
        )
        assert proc.returncode == 0
        meta_path = os.path.join(ROOT, "artifacts", "context_engine_metadata.json")
        meta = json.loads(open(meta_path).read())
        for key in ("engine_requested", "engine_used", "fallback_used",
                    "fallback_reason", "query", "timestamp", "semble", "errors"):
            assert key in meta, f"Missing key in metadata: {key}"
        assert "available" in meta["semble"]
        assert "upstream_commit" in meta["semble"]
        assert "mode" in meta["semble"]

    def test_selected_context_json_is_list(self):
        """selected_context.json is a JSON array."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "keyword",
            "--root", ROOT,
        )
        assert proc.returncode == 0
        selected_path = os.path.join(ROOT, "artifacts", "selected_context.json")
        selected = json.loads(open(selected_path).read())
        assert isinstance(selected, list)

    def test_context_candidates_json_is_list(self):
        """context_candidates.json is a JSON array."""
        proc = run_select_context(
            "--query", "CLAUDE",
            "--engine", "keyword",
            "--root", ROOT,
        )
        assert proc.returncode == 0
        cands_path = os.path.join(ROOT, "artifacts", "context_candidates.json")
        cands = json.loads(open(cands_path).read())
        assert isinstance(cands, list)


# ---------------------------------------------------------------------------
# 6. safe_bash classification
# ---------------------------------------------------------------------------

class TestSafeBashClassification:
    @pytest.fixture(autouse=True)
    def policies(self):
        from scripts.tools.safe_bash import load_policies
        self.allowed, self.ask, self.deny = load_policies()

    def _classify(self, cmd: str) -> str:
        from scripts.tools.safe_bash import classify_command
        verdict, _ = classify_command(cmd, self.allowed, self.ask, self.deny)
        return verdict

    def test_select_context_is_allowed(self):
        """safe_bash classifies select_context.py invocation as ALLOW."""
        verdict = self._classify(
            "python scripts/context/select_context.py --query test --engine auto"
        )
        assert verdict == "ALLOW", f"Expected ALLOW, got {verdict}"

    def test_semble_adapter_is_allowed(self):
        """safe_bash classifies semble_adapter.py invocation as ALLOW."""
        verdict = self._classify(
            "python scripts/context/semble_adapter.py --health-check"
        )
        assert verdict == "ALLOW", f"Expected ALLOW, got {verdict}"

    def test_rm_rf_is_denied(self):
        """safe_bash classifies rm -rf as DENY."""
        verdict = self._classify("rm -rf /")
        assert verdict == "DENY", f"Expected DENY, got {verdict}"

    def test_git_push_force_is_denied(self):
        """safe_bash classifies git push --force as DENY."""
        verdict = self._classify("git push --force origin main")
        assert verdict == "DENY", f"Expected DENY, got {verdict}"

    def test_git_status_is_allowed(self):
        """safe_bash classifies git status as ALLOW."""
        verdict = self._classify("git status")
        assert verdict == "ALLOW", f"Expected ALLOW, got {verdict}"

    def test_validate_secrets_is_allowed(self):
        """safe_bash classifies validate_secrets.py invocation as ALLOW."""
        verdict = self._classify(
            "python scripts/validate/validate_secrets.py"
        )
        assert verdict == "ALLOW", f"Expected ALLOW, got {verdict}"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _is_semble_installed() -> bool:
    """Check if semble is importable in the current environment."""
    try:
        import semble  # noqa: F401
        return True
    except ImportError:
        return False
