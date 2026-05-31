#!/usr/bin/env python
"""
Safe Bash Wrapper & Classifier
Classifies and executes commands based on safety policies.
"""
import sys
import os
import subprocess
import re
import json
import time
import shlex
import shutil

# Hardcoded fallback lists in case configs/tools.yaml is unavailable
DEFAULT_ALLOW = [
    r"^git\s+status$",
    r"^git\s+diff",
    r"^git\s+log",
    r"^git\s+branch",
    r"^rg\s+",
    r"^grep\s+",
    r"^python\s+-m\s+pytest",
    r"^pytest",
    r"^ruff\s+",
    r"^mypy"
]

DEFAULT_ASK = [
    r"^git\s+checkout",
    r"^git\s+restore",
    r"^git\s+clean",
    r"^pip\s+install",
    r"^npm\s+install"
]

DEFAULT_DENY = [
    r"rm\s+-rf",
    r"del\s+/s",
    r"format\s+",
    r"shutdown\s+",
    r"reboot",
    r"sudo\s+",
    r"chmod\s+-R\s+777",
    r"curl\s+.*\s*\|\s*bash",
    r"wget\s+.*\s*\|\s*bash",
    r"powershell\s+.*Invoke-WebRequest.*\|\s*iex",
    r"pwsh\s+.*Invoke-WebRequest.*\|\s*iex",
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard"
]

BASH_REQUIRED_BUT_NOT_FOUND = "BASH_REQUIRED_BUT_NOT_FOUND"


def command_requires_bash(cmd_str):
    """Return True when the command explicitly depends on bash."""
    cmd_clean = cmd_str.strip()
    if re.search(r"\|\s*bash(\s|$)", cmd_clean, re.IGNORECASE):
        return True

    try:
        parts = shlex.split(cmd_clean, posix=True)
    except ValueError:
        return False

    if not parts:
        return False

    executable = os.path.basename(parts[0]).lower()
    if executable in {"bash", "bash.exe"}:
        return True

    return any(part.lower().endswith((".sh", ".bash")) for part in parts)

def load_policies():
    """Load policies from configs/tools.yaml if exists, otherwise return defaults."""
    yaml_path = os.path.join("configs", "tools.yaml")
    if not os.path.exists(yaml_path):
        return DEFAULT_ALLOW, DEFAULT_ASK, DEFAULT_DENY
        
    try:
        # Simple regex lines parsing to avoid PyYAML dependencies in bootstrap phase
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        allowed = []
        ask = []
        deny = []
        
        current_section = None
        for line in content.splitlines():
            line_strip = line.strip()
            if not line_strip or line_strip.startswith("#"):
                continue
            if line_strip.endswith(":"):
                current_section = line_strip[:-1].lower()
                continue
            if line_strip.startswith("-"):
                val = line_strip[1:].strip().strip('"').strip("'")
                pattern = re.escape(val).replace(r"\*", ".*")
                if current_section == "allowed":
                    pattern = pattern.replace(r"\ ", r"\s+").replace(" ", r"\s+")
                    allowed.append(r"^" + pattern)
                elif current_section == "ask":
                    pattern = pattern.replace(r"\ ", r"\s+").replace(" ", r"\s+")
                    ask.append(r"^" + pattern)
                elif current_section == "deny":
                    pattern = pattern.replace(r"\ ", r"\s+.*").replace(" ", r"\s+.*")
                    deny.append(pattern)
                    
        return (allowed or DEFAULT_ALLOW), (ask or DEFAULT_ASK), (deny or DEFAULT_DENY)
    except Exception:
        return DEFAULT_ALLOW, DEFAULT_ASK, DEFAULT_DENY

def classify_command(cmd_str, allowed, ask, deny):
    """Classify the command string into ALLOW, ASK, or DENY."""
    cmd_clean = cmd_str.strip()
    
    # 1. Check Deny (highest priority, substring matching is safer for block lists)
    for pattern in deny:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return "DENY", f"Matches deny pattern: {pattern}"

    if command_requires_bash(cmd_clean) and shutil.which("bash") is None:
        return "DENY", BASH_REQUIRED_BUT_NOT_FOUND
            
    # 2. Check Allowed (exact or prefix matching)
    for pattern in allowed:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return "ALLOW", f"Matches allow pattern: {pattern}"
            
    # 3. Check Ask
    for pattern in ask:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return "ASK", f"Matches ask pattern: {pattern}"
            
    # 4. Default fallback: Unrecognized commands are categorized as ASK/DENY for safety
    return "ASK", "Unrecognized command, blocking by default."

def write_policy_decision(cmd, classification, reason):
    """Log the policy decision as a JSON line to tool_policy_decisions.jsonl."""
    os.makedirs("artifacts", exist_ok=True)
    decision = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": cmd,
        "classification": classification,
        "reason": reason
    }
    try:
        with open(os.path.join("artifacts", "tool_policy_decisions.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(decision) + "\n")
    except Exception:
        pass

def write_execution_log(cmd, start_time, end_time, exit_code):
    """Log the execution details as a JSON line to tool_execution_log.jsonl."""
    os.makedirs("artifacts", exist_ok=True)
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": cmd,
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
        "end_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(end_time)),
        "elapsed_seconds": end_time - start_time,
        "exit_code": exit_code
    }
    try:
        with open(os.path.join("artifacts", "tool_execution_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python safe_bash.py \"<command>\"")
        sys.exit(1)
        
    command = sys.argv[1]
    allowed, ask, deny = load_policies()
    
    classification, reason = classify_command(command, allowed, ask, deny)
    
    # Write policy decision log
    write_policy_decision(command, classification, reason)
    
    if classification == "DENY":
        print(f"[DENY] Safe Bash Blocked Command: '{command}'")
        print(f"Reason: {reason}")
        sys.exit(1)
        
    elif classification == "ASK":
        print(f"[ASK] Pre-execution Verification Required: '{command}'")
        print(f"Reason: {reason}")
        sys.exit(1)
        
    elif classification == "ALLOW":
        print(f"[ALLOW] Executing Safe Command: '{command}'")
        start_time = time.time()
        exit_code = 1
        try:
            # Run command and return its exit code
            res = subprocess.run(command, shell=True)
            exit_code = res.returncode
            sys.exit(exit_code)
        except Exception as e:
            print(f"[ERROR] Failed to execute command: {str(e)}")
            sys.exit(1)
        finally:
            end_time = time.time()
            write_execution_log(command, start_time, end_time, exit_code)

if __name__ == "__main__":
    main()
