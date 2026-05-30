# Skill: Code Modification (Editing)

## Overview
This skill governs how code edits are written, structured, and applied. It prioritizes surgical, localized modifications over wide-reaching, uncontrolled changes.

## Process Workflow

1. **Verify Context Alignment**:
   Confirm that any file you are about to edit is listed inside `artifacts/selected_context.json`. If a new file must be edited, update the selected context first with clear justifications.
2. **Apply Localized Changes**:
   * Make minimal, clean changes targeting only the requested logic.
   * Preserve all existing comments, docstrings, formatting, and structures.
   * Avoid sweeping refactorings unless explicitly mandated.
3. **Execute Post-Change Check**:
   Validate that syntax is correct and the code compiles without warnings.
