# CLAUDE.md: Project Memory & Guidelines

You are operating within `Claude_WindFaculty`, a specialized environment built to enhance and protect your coding operations.

## Core Operational Rules

1. **Primary Agent**: **Claude Code (Claude CLI)** is the primary coding agent. Do not attempt to build, clone, or run a replacement agent runtime, planner, or executor. 
2. **No Success Without Proof**: You must **never** claim success for a task without generating and validating actual `git diff` outputs, running relevant tests, and producing an execution report.
3. **Use the Environment**: Leverage the scripts, skills, hooks, and subagents provided in this repository to maximize work quality, safety, and token efficiency.
4. **Safety & Command Rules**: Do not execute blocked bash commands directly. Always pass terminal commands through the safe bash hook or `scripts/tools/safe_bash.py` classifier where required.

---

## Build & Test Commands

* **Run Test Suite**: `python -m pytest`
* **Run Test Suite (Quiet Mode)**: `python -m pytest -q`
* **Validate Environment**: `python scripts/bootstrap/verify_environment.py`
* **Safe Bash Command execution**: `python scripts/tools/safe_bash.py "<command>"`
* **Validate Diff**: `python scripts/validate/validate_diff.py`
* **Generate Report**: `python scripts/reports/write_report.py`

---

## Code Quality & Architecture

* **Language**: Python 3.8+ (for system scripts).
* **Dependencies**: Keep external dependencies extremely light. Prefer the Python standard library.
* **Testing**: Write comprehensive pytest unit tests for every new script, especially safe wrappers and validators.
* **Structure**: Maintain absolute separation between custom developer tools (in `scripts/`) and temporary artifacts/logs (in `artifacts/` or `reports/`).

---

## Definition of Done (DoD)

A task is only considered completed when:
1. All changes are correctly reflected in `git diff`.
2. Diff contains no suspicious generated or binary files and has been parsed by `scripts/validate/validate_diff.py`.
3. Unit tests pass successfully (with exit code 0).
4. No secrets or credentials have been committed.
5. An execution summary is compiled into a report in `reports/`.
