#!/usr/bin/env python

"""
Claude hook execution reliability validator (Enhanced).

This gate validates configured Claude hooks without executing the hook commands.
Enhanced features include:
- Config readability, command parsing, referenced local scripts
- Basic script syntax validation for Python and shell hooks
- Executable permission checks for shell scripts (Unix-like systems)
- Hook dependency analysis
- Configuration audit and best-practice recommendations
"""
import argparse
import json
import os
import platform
import py_compile
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path


DEFAULT_CONFIG = Path(".claude") / "settings.json"
PYTHON_INTERPRETERS = {"python", "python3", "python.exe", "py"}
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash"}
POWERSHELL_INTERPRETERS = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".ps1"}


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _as_posix(path):
    return str(path).replace("\\", "/")


def _is_interpreter(token, names):
    return Path(token).name.lower() in names


def _looks_like_local_script(token):
    path = Path(token)
    return path.suffix.lower() in SCRIPT_EXTENSIONS and (
        "/" in token or "\\" in token or not path.is_absolute()
    )


def _resolve_local_path(token, repo_root):
    path = Path(token)
    if path.is_absolute():
        candidate = path.resolve()
    else:
        candidate = (repo_root / path).resolve()

    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return candidate


def _script_token_from_parts(parts):
    if not parts:
        return None

    executable = parts[0]
    if _is_interpreter(executable, PYTHON_INTERPRETERS):
        idx = 1
        while idx < len(parts):
            token = parts[idx]
            if token in {"-m", "-c"}:
                return None
            if token.startswith("-"):
                idx += 1
                continue
            return token if _looks_like_local_script(token) else None
        return None

    if _is_interpreter(executable, SHELL_INTERPRETERS):
        for token in parts[1:]:
            if token.startswith("-"):
                continue
            return token if _looks_like_local_script(token) else None
        return None

    if _is_interpreter(executable, POWERSHELL_INTERPRETERS):
        for idx, token in enumerate(parts[1:], start=1):
            if token.lower() == "-file" and idx + 1 < len(parts):
                candidate = parts[idx + 1]
                return candidate if _looks_like_local_script(candidate) else None
        return None

    return executable if _looks_like_local_script(executable) else None


def _iter_commands_for_entry(event, entry, prefix):
    if entry is None or entry == "" or entry == [] or entry == {}:
        yield {
            "event": event,
            "location": prefix,
            "command": None,
            "status": "skipped",
            "reason": "empty_hook",
        }
        return

    if isinstance(entry, str):
        yield {"event": event, "location": prefix, "command": entry}
        return

    if not isinstance(entry, dict):
        yield {
            "event": event,
            "location": prefix,
            "command": None,
            "status": "failed",
            "reason": "malformed_hook_entry",
        }
        return

    command = entry.get("run") or entry.get("command")
    if isinstance(command, str):
        yield {"event": event, "location": prefix, "command": command}

    nested_hooks = entry.get("hooks")
    if isinstance(nested_hooks, list):
        if not nested_hooks:
            yield {
                "event": event,
                "location": prefix + ".hooks",
                "command": None,
                "status": "skipped",
                "reason": "empty_hook_list",
            }
        for idx, nested in enumerate(nested_hooks):
            yield from _iter_commands_for_entry(event, nested, f"{prefix}.hooks[{idx}]")

    if command is None and nested_hooks is None:
        yield {
            "event": event,
            "location": prefix,
            "command": None,
            "status": "failed",
            "reason": "missing_hook_command",
        }


def _iter_hook_commands(hooks):
    if hooks in (None, {}, []):
        yield {
            "event": None,
            "location": "hooks",
            "command": None,
            "status": "skipped",
            "reason": "empty_hooks",
        }
        return

    if not isinstance(hooks, dict):
        yield {
            "event": None,
            "location": "hooks",
            "command": None,
            "status": "failed",
            "reason": "hooks_must_be_object",
        }
        return

    for event, entries in hooks.items():
        if entries in (None, [], {}):
            yield {
                "event": event,
                "location": f"hooks.{event}",
                "command": None,
                "status": "skipped",
                "reason": "empty_hook_event",
            }
            continue

        if isinstance(entries, list):
            for idx, entry in enumerate(entries):
                yield from _iter_commands_for_entry(event, entry, f"hooks.{event}[{idx}]")
        else:
            yield from _iter_commands_for_entry(event, entries, f"hooks.{event}")


def _check_python_syntax(script_path):
    try:
        py_compile.compile(str(script_path), doraise=True)
    except py_compile.PyCompileError as exc:
        return False, str(exc)
    return True, "python_compile_ok"


def _check_shell_syntax(script_path):
    bash = shutil.which("bash")
    if not bash:
        return None, "bash_not_available"

    result = subprocess.run(
        [bash, "-n", str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "shell_syntax_error").strip()
    return True, "shell_parse_ok"


def _check_script_syntax(script_path):
    suffix = script_path.suffix.lower()
    if suffix == ".py":
        ok, detail = _check_python_syntax(script_path)
        return {
            "status": "passed" if ok else "failed",
            "check": "python_compile",
            "detail": detail,
        }

    if suffix in {".sh", ".bash"}:
        ok, detail = _check_shell_syntax(script_path)
        if ok is None:
            return {"status": "skipped", "check": "shell_parse", "detail": detail}
        return {
            "status": "passed" if ok else "failed",
            "check": "shell_parse",
            "detail": detail,
        }

    if suffix == ".ps1":
        return {"status": "skipped", "check": "powershell_parse", "detail": "not_implemented"}

    return {"status": "skipped", "check": "unsupported_script_type", "detail": suffix}


def _check_executable_permission(script_path):
    """Check if shell scripts have executable permission on Unix-like systems."""
    if platform.system() == "Windows":
        return {"status": "skipped", "reason": "windows_system_no_exec_check"}

    suffix = script_path.suffix.lower()
    if suffix not in {".sh", ".bash"}:
        return {"status": "skipped", "reason": "not_shell_script"}

    try:
        file_stat = os.stat(str(script_path))
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
        if is_executable:
            return {"status": "passed", "reason": "executable_permission_set"}
        else:
            return {"status": "warning", "reason": "executable_permission_missing"}
    except (OSError, IOError) as exc:
        return {"status": "failed", "reason": f"permission_check_failed: {exc}"}


def _collect_hook_dependencies(report):
    """Analyze dependencies between hooks and identify potential ordering issues."""
    dependencies = {}
    for hook in report["hooks"]:
        script = hook.get("script")
        if script and hook.get("status") != "failed":
            dependencies[script] = {
                "event": hook.get("event"),
                "location": hook.get("location"),
            }
    return dependencies


def _audit_config_best_practices(config, report):
    """Generate audit recommendations for configuration best practices."""
    audit = {"recommendations": [], "info": []}

    if not config.get("hooks"):
        audit["info"].append("No hooks configured (this may be intentional)")
        return audit

    hooks = config.get("hooks", {})
    hook_count = sum(1 for _ in _iter_hook_commands(hooks) if _ not in (None, {}))

    if hook_count > 5:
        audit["recommendations"].append(
            "CONSIDER: More than 5 hooks may impact performance; review for consolidation"
        )

    if "PreToolUse" in hooks and isinstance(hooks.get("PreToolUse"), list):
        if len(hooks["PreToolUse"]) > 3:
            audit["recommendations"].append("PreToolUse has many hooks; review for efficiency")

    return audit


def _validate_command(command, repo_root):
    if not isinstance(command, str) or not command.strip():
        return {
            "command": command,
            "status": "failed",
            "reason": "empty_command",
            "issues": ["MALFORMED_COMMAND"],
        }

    try:
        parts = shlex.split(command, posix=True)
    except ValueError as exc:
        return {
            "command": command,
            "status": "failed",
            "reason": "command_parse_error",
            "detail": str(exc),
            "issues": ["MALFORMED_COMMAND"],
        }

    if not parts:
        return {
            "command": command,
            "status": "failed",
            "reason": "empty_command",
            "issues": ["MALFORMED_COMMAND"],
        }

    script_token = _script_token_from_parts(parts)
    if script_token is None:
        return {
            "command": command,
            "status": "skipped",
            "reason": "no_local_script_reference",
            "argv": parts,
            "issues": [],
        }

    script_path = _resolve_local_path(script_token, repo_root)
    if script_path is None:
        return {
            "command": command,
            "status": "failed",
            "reason": "script_outside_repo",
            "script": script_token,
            "argv": parts,
            "issues": ["SCRIPT_OUTSIDE_REPO"],
        }

    rel_script = _as_posix(script_path.relative_to(repo_root))
    if not script_path.exists():
        return {
            "command": command,
            "status": "failed",
            "reason": "missing_script",
            "script": rel_script,
            "argv": parts,
            "issues": ["MISSING_SCRIPT"],
        }

    if not script_path.is_file():
        return {
            "command": command,
            "status": "failed",
            "reason": "script_not_file",
            "script": rel_script,
            "argv": parts,
            "issues": ["SCRIPT_NOT_FILE"],
        }

    syntax = _check_script_syntax(script_path)
    status = "failed" if syntax["status"] == "failed" else "passed"
    issues = ["SCRIPT_SYNTAX_ERROR"] if status == "failed" else []

    result = {
        "command": command,
        "status": status,
        "reason": syntax["detail"],
        "script": rel_script,
        "argv": parts,
        "syntax": syntax,
        "issues": issues,
    }

    perm_check = _check_executable_permission(script_path)
    result["permissions"] = perm_check

    return result


def validate_claude_hooks(
    config_path=DEFAULT_CONFIG,
    repo_root=None,
    enable_audit=True,
    enable_dependency_analysis=True,
):
    repo_root = Path(repo_root or _repo_root()).resolve()
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    report = {
        "validator": "claude_hook_execution_reliability_gate_enhanced",
        "config": _as_posix(config_path.relative_to(repo_root))
        if config_path.exists()
        else _as_posix(config_path),
        "passed": False,
        "verdict": "FAIL",
        "summary": {"passed": 0, "failed": 0, "skipped": 0, "warned": 0, "total": 0},
        "hooks": [],
        "issues": [],
        "audit": None,
        "dependencies": None,
    }

    if not config_path.exists():
        report["issues"].append("CONFIG_NOT_FOUND")
        return report

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        report["issues"].append("INVALID_JSON")
        report["error"] = str(exc)
        return report

    for hook in _iter_hook_commands(config.get("hooks")):
        if hook.get("status") in {"skipped", "failed"} and hook.get("command") is None:
            result = hook
            result.setdefault(
                "issues", [] if result["status"] == "skipped" else [result["reason"].upper()]
            )
        else:
            result = hook.copy()
            result.update(_validate_command(hook["command"], repo_root))

        report["hooks"].append(result)
        report["summary"]["total"] += 1
        status = result.get("status", "unknown")
        if status in report["summary"]:
            report["summary"][status] += 1
        report["issues"].extend(result.get("issues", []))

        if result.get("permissions", {}).get("status") == "warning":
            report["summary"]["warned"] += 1

    if enable_audit:
        report["audit"] = _audit_config_best_practices(config, report)

    if enable_dependency_analysis:
        report["dependencies"] = _collect_hook_dependencies(report)

    if report["summary"]["failed"] == 0 and report["summary"]["warned"] == 0:
        report["passed"] = True
        report["verdict"] = "PASS"

    report["issues"] = sorted(set(report["issues"]))
    return report


def _print_human(report):
    print(f"[{report['verdict']}] Claude Hook Execution Reliability Gate (Enhanced)")
    print(f"Config: {report['config']}")
    summary = report["summary"]
    print(
        "Hooks: "
        f"{summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['warned']} warned, {summary['skipped']} skipped, {summary['total']} total"
    )
    for hook in report["hooks"]:
        location = hook.get("location", "hooks")
        command = hook.get("command") or "<empty>"
        detail = hook.get("reason", "")
        status = hook["status"].upper()
        print(f"- {status} {location}: {command} {detail}".rstrip())
        if hook.get("permissions", {}).get("status") == "warning":
            print(f"  └─ WARNING: {hook['permissions']['reason']}")

    if report.get("audit", {}).get("recommendations"):
        print("\nAudit Recommendations:")
        for rec in report["audit"]["recommendations"]:
            print(f"  • {rec}")

    if report.get("dependencies"):
        print(f"\nDependencies: {len(report['dependencies'])} script(s) referenced")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate Claude hook configuration without executing hooks."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Claude settings JSON path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Disable configuration audit recommendations.",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Disable dependency analysis.",
    )
    args = parser.parse_args(argv)

    report = validate_claude_hooks(
        args.config,
        enable_audit=not args.no_audit,
        enable_dependency_analysis=not args.no_deps,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
