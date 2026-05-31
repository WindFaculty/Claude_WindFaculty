import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.validate.validate_claude_hooks import validate_claude_hooks


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_validate_current_claude_hook_config():
    report = validate_claude_hooks()
    assert report["passed"] is True
    assert report["verdict"] == "PASS"
    assert report["summary"]["failed"] == 0
    assert any(hook.get("script") == "scripts/tools/safe_bash.py" for hook in report["hooks"])


def test_empty_hooks_are_skipped_without_failure(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": []}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is True
    assert report["summary"]["skipped"] == 1
    assert report["hooks"][0]["reason"] == "empty_hook_event"


def test_hook_command_with_space_path_and_arguments(tmp_path):
    script = tmp_path / "scripts" / "hook dir" / "valid hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(
        config,
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "tools": ["Bash"],
                        "run": 'python "scripts/hook dir/valid hook.py" --mode check',
                    }
                ]
            }
        },
    )

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is True
    assert report["hooks"][0]["script"] == "scripts/hook dir/valid hook.py"
    assert report["hooks"][0]["argv"][-2:] == ["--mode", "check"]


def test_missing_script_fails(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "python scripts/missing.py"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
    assert report["verdict"] == "FAIL"
    assert "MISSING_SCRIPT" in report["issues"]


def test_python_syntax_error_fails(tmp_path):
    script = tmp_path / "scripts" / "bad_hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("def broken(:\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "python scripts/bad_hook.py"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
    assert "SCRIPT_SYNTAX_ERROR" in report["issues"]


def test_invalid_json_fails(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    config.parent.mkdir(parents=True)
    config.write_text("{ invalid json", encoding="utf-8")

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
    assert "INVALID_JSON" in report["issues"]


def test_malformed_command_fails(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": 'python "unterminated'}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
    assert "MALFORMED_COMMAND" in report["issues"]


def test_enhanced_validator_includes_permissions_check(tmp_path):
    script = tmp_path / "scripts" / "hook.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "bash scripts/hook.sh"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is True
    assert report["hooks"][0].get("permissions") is not None
    assert report["hooks"][0]["permissions"]["status"] in {"passed", "warning", "skipped"}


def test_audit_report_is_generated(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "python scripts/valid.py"}]}})
    script = tmp_path / "scripts" / "valid.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    report = validate_claude_hooks(config, repo_root=tmp_path, enable_audit=True)

    assert "audit" in report
    assert "recommendations" in report["audit"]
    assert "info" in report["audit"]


def test_audit_can_be_disabled(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "python scripts/valid.py"}]}})
    script = tmp_path / "scripts" / "valid.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    report = validate_claude_hooks(config, repo_root=tmp_path, enable_audit=False)

    assert report["audit"] is None


def test_dependency_analysis_is_collected(tmp_path):
    script = tmp_path / "scripts" / "hook.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('ok')\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "python scripts/hook.py"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path, enable_dependency_analysis=True)

    assert "dependencies" in report
    assert "scripts/hook.py" in report["dependencies"]
    assert report["dependencies"]["scripts/hook.py"]["event"] == "PreToolUse"


def test_dependency_analysis_can_be_disabled(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": []}})

    report = validate_claude_hooks(config, repo_root=tmp_path, enable_dependency_analysis=False)

    assert report["dependencies"] is None


def test_enhanced_validator_tracks_warned_count(tmp_path):
    script = tmp_path / "scripts" / "hook.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "bash scripts/hook.sh"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert "warned" in report["summary"]
    assert report["summary"]["warned"] >= 0
