# Skill: Final Execution Report Compiler

## Overview
Use this skill at the final step of task resolution. It consolidates verification steps, diff outcomes, and test logs into a single robust execution file.

## Process Workflow

1. **Verify Evidence Pipeline**:
   Ensure all target outputs exist in `artifacts/`:
   * `artifacts/selected_context.json`
   * `artifacts/diff_review.json`
2. **Execute Report Compilation Script**:
   Synthesize all metrics, files changed, and test results using the reporting generator:
   ```bash
   python scripts/reports/write_report.py
   ```
3. **Audit Tone**:
   Maintain a strict professional, objective tone. Avoid overclaims, superlatives, and unverified confirmations.

## Expected Deliverables
* A formal execution report in `reports/` summarizing everything.
