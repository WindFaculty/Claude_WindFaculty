#!/usr/bin/env python
"""
Safe Bash Wrapper & Classifier
Classifies and executes commands based on safety policies.
"""
import sys
import os
import subprocess
import re

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
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard"
]

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python safe_bash.py \"<command>\"")
        sys.exit(1)
        
    command = sys.argv[1]
    allowed, ask, deny = load_policies()
    
    classification, reason = classify_command(command, allowed, ask, deny)
    
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
        try:
            # Run command and return its exit code
            res = subprocess.run(command, shell=True)
            sys.exit(res.returncode)
        except Exception as e:
            print(f"[ERROR] Failed to execute command: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
