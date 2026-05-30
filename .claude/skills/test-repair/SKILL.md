# Skill: Test Repair & Failure Diagnostics

## Overview
Use this skill when test failures are encountered during the validation loop. It outlines structured steps to diagnose regressions and apply minimal repairs.

## Process Workflow

1. **Verify Failures**:
   Run the pytest suite to gather baseline execution failure metrics:
   ```bash
   python -m pytest
   ```
2. **Execute Diagnoser**:
   Delegate stack trace reading to a subagent (`test-diagnoser.md`) or capture the raw dump manually. Keep log summaries in `artifacts/test_failure_summary.json`.
3. **Formulate a Repair Plan**:
   Define the exact changes needed to resolve the regression in `artifacts/repair_plan.json`.
4. **Surgical Fix & Re-test**:
   Apply the logic fixes and re-execute the target test immediately.
   ```bash
   python -m pytest <path_to_failed_test>.py
   ```

## Expected Deliverables
* `artifacts/test_failure_summary.json`
* `artifacts/repair_plan.json`
