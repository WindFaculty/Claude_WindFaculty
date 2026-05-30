# Benchmark Task 002: Secure Credentials Filter Refactoring

## Description
Optimize regex parsing efficiency inside `validate_secrets.py` to prevent catastrophic backtracking when scanning massive, compiled code assets.

## Requirements
1. Refactor key pattern matcher list compiled in `configs/validation.yaml` to avoid nesting quantifiers.
2. Ensure file scan logic correctly bypasses generated assets while remaining lightweight.
3. Validate that standard unit tests for security leak scanning pass.

## Targeted Files
* `scripts/validate/validate_secrets.py`
* `configs/validation.yaml`
