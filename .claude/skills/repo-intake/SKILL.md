# Skill: Repository Intake

## Overview
Use this skill when onboarding into a new repository or starting a fresh coding session. It ensures alignment on workspace rules, directory layouts, and dependency state before any changes are introduced.

## Process Workflow

1. **Verify environment details**:
   Run the system verifier script to ensure core dependencies exist:
   ```bash
   python scripts/bootstrap/verify_environment.py
   ```
2. **Scan the directory structure**:
   Review file paths, configuration files in `configs/`, and project memories in `CLAUDE.md`.
3. **Write initial state**:
   Document the current Git metadata, file footprint counts, and workspace statistics by executing:
   ```bash
   python scripts/bootstrap/repo_intake.py
   ```

## Expected Deliverables
* `artifacts/repo_intake.json`
* A structured markdown summary in `reports/repo_intake.md`.
