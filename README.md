# Claude_WindFaculty

A robust, supportive operating environment built specifically to complement **Claude Code** (Claude CLI). 

> [!IMPORTANT]
> This repository **does not** implement a custom agent runtime, planner, or executor. Claude Code is the primary coding agent. This environment provides the memory layer (`CLAUDE.md`), pre-tool hooks, validation utilities, context selectors, testing scaffolds, and execution logs to ensure Claude Code runs safely, efficiently, and effectively.

## Architecture & Ecosystem

```
Claude Code / Claude CLI
├── Project Memory: CLAUDE.md
├── Settings & Hooks: .claude/settings.json
├── Specialist Subagents: .claude/agents/
├── Process Skills: .claude/skills/
├── Safe wrappers & Guards: scripts/tools/
├── Context & AST Filters: scripts/context/
├── Diff & Secret Validators: scripts/validate/
└── Execution Reports: reports/
```

## Key Features

1. **Safety First**: Safe wrappers for bash commands prevent destructive operations (e.g., `rm -rf`, `git push --force`).
2. **Context Compacting**: Integrations with AST-based selectors to filter and bundle context, avoiding token bloat.
3. **Rigorous Validation**: Pre-commit style validations to verify diffs, run tests, and check for secrets before claiming task success.
4. **Structured Output**: Automatic execution summaries, reports, and benchmark metrics for every completed run.

## Setup

Refer to `scripts/bootstrap/verify_environment.py` and run it:
```bash
python scripts/bootstrap/verify_environment.py
```
