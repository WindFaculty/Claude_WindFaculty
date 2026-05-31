#!/usr/bin/env python3
import sys
import os
import json
import time
import subprocess

def log_decision(tool, command, delegate, decision, reason):
    """Write the audit log to logs/ecc/hooks.jsonl."""
    os.makedirs(os.path.join("logs", "ecc"), exist_ok=True)
    log_entry = {
        "event": "PreToolUse",
        "tool": tool,
        "delegate": delegate,
        "command": command,
        "decision": decision,
        "reason": reason,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "Claude_WindFaculty+everything-claude-code"
    }
    try:
        with open(os.path.join("logs", "ecc", "hooks.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

def main():
    # 1. Try to read from stdin (Claude PreToolUse JSON payload)
    stdin_data = ""
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
        except Exception:
            pass

    command = ""
    tool = "Bash"
    delegate = "scripts/tools/safe_bash.py"

    # Basic parsing of --tool and --delegate if passed
    for i in range(len(sys.argv)):
        if sys.argv[i] == "--tool" and i + 1 < len(sys.argv):
            tool = sys.argv[i+1]
        elif sys.argv[i] == "--delegate" and i + 1 < len(sys.argv):
            delegate = sys.argv[i+1]

    # Try parsing stdin as JSON
    if stdin_data:
        try:
            payload = json.loads(stdin_data)
            if "arguments" in payload and isinstance(payload["arguments"], dict):
                command = payload["arguments"].get("command", "")
            elif "tool_input" in payload and isinstance(payload["tool_input"], dict):
                command = payload["tool_input"].get("command", "")
            elif "input" in payload and isinstance(payload["input"], dict):
                command = payload["input"].get("command", "")
            if not command and "command" in payload:
                command = payload.get("command", "")
            if "tool" in payload:
                tool = payload.get("tool", tool)
        except Exception:
            pass

    # If stdin didn't give us a command, look for command strings in sys.argv
    if not command:
        args = [a for a in sys.argv[1:] if not a.startswith("-") and a not in ["Bash", "scripts/tools/safe_bash.py"]]
        if args:
            command = args[-1]

    command = command.strip()

    # If we still don't have a command, log it and pass-through
    if not command:
        log_decision(tool, "N/A", delegate, "allow", "No command extracted, passing through")
        sys.exit(0)

    # 2. Invoke the delegate safe_bash.py
    # Since we want to preserve safe_bash.py's exit code and stream outputs,
    # we run the subprocess and let stdout/stderr pass through.
    try:
        # Run delegate python scripts/tools/safe_bash.py "<command>"
        res = subprocess.run([sys.executable, delegate, command])
        exit_code = res.returncode

        decision = "allow" if exit_code == 0 else "block"
        reason = f"Executed with exit code {exit_code}"
        
        log_decision(tool, command, delegate, decision, reason)
        sys.exit(exit_code)
            
    except Exception as e:
        decision = "block"
        reason = f"Bridge exception during delegation: {str(e)}"
        print(f"[ERROR] Bridge failed to delegate: {str(e)}", file=sys.stderr)
        log_decision(tool, command, delegate, decision, reason)
        sys.exit(1)

if __name__ == "__main__":
    main()
