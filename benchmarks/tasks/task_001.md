# Benchmark Task 001: Environment Variable Parser Robustness

## Description
Simulate fixing config loading edge-cases for `.env` credentials parsing, ensuring spaces around `=` do not disrupt extraction.

## Requirements
1. Verify that `load_secret_patterns` in `validate_secrets.py` correctly parses regex strings with multi-line backslash overrides.
2. Assert that a sample config with trailing spaces evaluates to expected key-value pairs.
3. Validate that standard environment checks do not crash if `.env` has trailing carriage returns.

## Targeted Files
* `scripts/validate/validate_secrets.py`
* `tests/test_validation.py`
