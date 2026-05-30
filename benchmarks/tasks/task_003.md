# Benchmark Task 003: Restricted Repository Ingestion Intake

## Description
Simulate workspace intake scans on restricted, minimal checkouts where git history or statistics are partially missing.

## Requirements
1. Verify `repo_intake.py` handles systems without a valid git binary gracefully.
2. Assert that missing git tags do not crash metadata capture.
3. Validate that file stats aggregation successfully isolates python code blocks from cached resources.

## Targeted Files
* `scripts/bootstrap/repo_intake.py`
* `reports/repo_intake.md`
