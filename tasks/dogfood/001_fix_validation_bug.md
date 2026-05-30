# Dogfood Task: Fix Pytest Quiet Mode Validation Bug

## Description
In `scripts/validate/validate_tests.py`, the regex parsing of `pytest` output summary is fragile. Specifically, when executing pytest in quiet mode (`pytest -q`), it omits the boundary markers `===` (e.g., printing `49 passed in 8.35s`). This causes the parser to fail to match the summary line, fall back to a basic keyword scan for `PASSED`/`FAILED`, and miscount the word `FAILED` inside logging file paths, which flags false failures.

## Requirements
1. Modify `parse_test_metrics` inside `scripts/validate/validate_tests.py` to backward-scan and extract metrics from pytest summaries with or without double-equal boundary markers (`===`).
2. Support extracting `passed`, `failed`, and `skipped` counts robustly.
3. Pass all unit tests in `tests/test_validation.py` including quiet mode assertions.

## Targeted Files
* `scripts/validate/validate_tests.py`
* `tests/test_validation.py`
