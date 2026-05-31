# Claude_WindFaculty Verification Profile

Minimum checks:
1. Validate JSON files:
   python -m json.tool .claude/settings.json

2. Validate Python scripts:
   python -m py_compile scripts/tools/safe_bash.py
   python -m py_compile scripts/integrations/ecc/ecc_hook_bridge.py

3. Run everything-claude-code tests if Node is available:
   cd third_party/everything-claude-code
   node tests/run-all.js

4. Check no active MCP secrets:
   search for YOUR_*_HERE placeholders in active config

5. Check hook schema:
   .claude/settings.json must use PreToolUse array schema.
