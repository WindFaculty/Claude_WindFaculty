# Skill: Context Packing

## Overview
Use this skill before starting any code modification tasks. It guides you in locating and packing files to form a precise, high-fidelity context packet without token bloat.

## Process Workflow

1. **Extract Search Keywords**:
   Read the problem statement or task file (e.g. `tasks/examples/sample_task.md`) and extract key class names, symbols, or method signatures.
2. **Execute Context Selection Script**:
   Call the selector script to retrieve relevant files based on search patterns or import graphs:
   ```bash
   python scripts/context/select_context.py --query "keyword"
   ```
3. **Establish Budget Guardrails**:
   Read `configs/context.yaml` and confirm the file count falls under the budget limits. Never pack more than 20 files.
4. **Compile Selected Packet**:
   Write details of the selected workspace files to `artifacts/selected_context.json` stating why each file is relevant.

## Expected Deliverables
* `artifacts/selected_context.json`
* `artifacts/context_pack.md` (summary description of context files)
