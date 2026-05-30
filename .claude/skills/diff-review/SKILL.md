# Skill: Diff & Impact Review

## Overview
Use this skill prior to concluding any task execution. It forces structured audits of active git changes to ensure correctness, cleanliness, and safety.

## Process Workflow

1. **Execute Diff Validator**:
   Run the automated diff scanner to verify structure, count files, and look for anomalous file extensions:
   ```bash
   python scripts/validate/validate_diff.py
   ```
2. **Scan for Secret Exposures**:
   Verify no credentials, keys, or environmental `.env` files are tracked:
   ```bash
   python scripts/validate/validate_secrets.py
   ```
3. **Write Review Report**:
   Compile the validator outcomes into `artifacts/diff_review.json` to prove verification has occurred.

## Expected Deliverables
* `artifacts/diff_review.json`
* `artifacts/patch_acceptance.json`
