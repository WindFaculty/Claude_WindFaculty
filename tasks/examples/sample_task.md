# Sample Task: Implement Environment Validation Tests

## Description
Write pytest cases to verify that `safe_bash.py` correctly blocks banned commands and allows valid commands.

## Requirements
1. Test command classification against the default lists.
2. Assert `rm -rf` is categorized as `DENY`.
3. Assert `git status` is categorized as `ALLOW`.
4. Ensure pytest execution returns exit code 0.

## Targeted Files
* `scripts/tools/safe_bash.py`
* `tests/test_safe_bash.py`
