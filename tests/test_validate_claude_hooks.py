import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.validate.validate_claude_hooks import validate_claude_hooks


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def run_git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def init_git_repo(tmp_path, subject="fixture commit"):
    run_git(tmp_path, "init")
    run_git(tmp_path, "checkout", "-b", "main")
    run_git(tmp_path, "config", "user.email", "test@example.com")
    run_git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / ".claude").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "hook.py").write_text("print('ok')\n", encoding="utf-8")
    write_json(tmp_path / ".claude" / "settings.json", {"hooks": {"PreToolUse": [{"run": "python scripts/hook.py"}]}})
    run_git(tmp_path, "add", ".")
    run_git(tmp_path, "commit", "-m", subject)
    return tmp_path


def write_benchmark_report(repo, head=None, subject="fixture commit", changed_files=None, verdict="PASS"):
    head = head or run_git(repo, "rev-parse", "HEAD").stdout.strip()
    changed_files = changed_files or []
    report = repo / "reports" / "hook_reliability_gate_benchmark.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    files = "\n".join(f"- {path}" for path in changed_files) or "- none"
    report.write_text(
        "\n".join(
            [
                "# Claude Hook Reliability Gate Benchmark Report",
                "## Git Metadata",
                "Branch: main",
                f"HEAD: {head}",
                f"Commit subject: {subject}",
                "Base: main",
                "## Files Changed",
                files,
                "## Tests Run",
                "- python -m pytest tests/test_safe_bash.py tests/test_validate_claude_hooks.py -q",
                "## Verdict",
                verdict,
                "## Known limitations / Remaining risk",
                "- none recorded",
            ]
        ),
        encoding="utf-8",
    )
    return report


def create_feature_commit(repo, path="changed.txt", content="changed\n", subject="feature change"):
    run_git(repo, "checkout", "-b", "feature")
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run_git(repo, "add", path)
    run_git(repo, "commit", "-m", subject)
    return path, run_git(repo, "rev-parse", "HEAD").stdout.strip()


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


def test_validator_fails_on_missing_hook_target_file(tmp_path):
    test_missing_script_fails(tmp_path)


def test_validator_fails_on_hook_command_that_points_to_nonexistent_script(tmp_path):
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "./scripts/missing.sh"}]}})

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
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


def test_bash_required_missing_bash_fails(tmp_path, monkeypatch):
    script = tmp_path / "scripts" / "hook.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    config = tmp_path / ".claude" / "settings.json"
    write_json(config, {"hooks": {"PreToolUse": [{"run": "bash scripts/hook.sh"}]}})
    monkeypatch.setattr("scripts.validate.validate_claude_hooks.shutil.which", lambda name: None)

    report = validate_claude_hooks(config, repo_root=tmp_path)

    assert report["passed"] is False
    assert "BASH_REQUIRED_BUT_NOT_FOUND" in report["issues"]


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


def test_report_must_be_tracked_or_validator_fails(tmp_path):
    repo = init_git_repo(tmp_path)
    (repo / ".gitignore").write_text("reports/*\n", encoding="utf-8")
    write_benchmark_report(repo)

    report = validate_claude_hooks(repo / ".claude" / "settings.json", repo_root=repo)

    assert report["passed"] is False
    assert "BENCHMARK_REPORT_GIT_IGNORED" in report["issues"]


def test_commit_subject_must_match_git_log(tmp_path):
    repo = init_git_repo(tmp_path)
    changed_file, head = create_feature_commit(repo, subject="real subject")
    write_benchmark_report(repo, head=head, subject="stale subject", changed_files=[changed_file])

    report = validate_claude_hooks(repo / ".claude" / "settings.json", repo_root=repo)

    assert report["passed"] is False
    assert "BENCHMARK_REPORT_COMMIT_SUBJECT_MISMATCH" in report["issues"]


def test_report_file_list_must_match_git_diff(tmp_path):
    repo = init_git_repo(tmp_path)
    _changed_file, head = create_feature_commit(repo, subject="real subject")
    write_benchmark_report(repo, head=head, subject="real subject", changed_files=["other.txt"])

    report = validate_claude_hooks(repo / ".claude" / "settings.json", repo_root=repo)

    assert report["passed"] is False
    assert "BENCHMARK_REPORT_CHANGED_FILES_MISMATCH" in report["issues"]


def test_report_cannot_claim_all_pass_when_any_skip_or_not_run_exists(tmp_path):
    repo = init_git_repo(tmp_path)
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    report_path = write_benchmark_report(repo, head=head, subject="fixture commit", verdict="all tests pass")
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\n- SKIPPED: test_name\n",
        encoding="utf-8",
    )

    report = validate_claude_hooks(repo / ".claude" / "settings.json", repo_root=repo)

    assert report["passed"] is False
    assert "BENCHMARK_REPORT_OVERCLAIM" in report["issues"]
