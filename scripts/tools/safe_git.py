#!/usr/bin/env python
"""
Safe Git Command Execution Wrapper
Ensures no destructive git actions (e.g. force push, hard reset) are run.
"""
import sys
import subprocess

def is_safe_git_command(args):
    """Scan arguments for destructive patterns."""
    args_str = " ".join(args).lower()
    
    # Destructive commands block list
    if "push" in args and ("--force" in args or "-f" in args):
        return False, "Force pushes are restricted in this environment."
    if "reset" in args and "--hard" in args:
        return False, "Hard resets are restricted; use soft reset or git restore instead."
    if "clean" in args and ("-f" in args or "--force" in args or "-x" in args):
        return False, "Force cleaning is restricted to prevent data loss."
        
    return True, "Safe Command"

def main():
    if len(sys.argv) < 2:
        print("Usage: python safe_git.py <git args...>")
        sys.exit(1)
        
    git_args = sys.argv[1:]
    is_safe, msg = is_safe_git_command(git_args)
    
    if not is_safe:
        print(f"[BLOCKED] Destructive Git Action Blocked: {msg}")
        sys.exit(1)
        
    cmd = ["git"] + git_args
    print(f"[EXECUTE] Running safe git command: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    except Exception as e:
        print(f"[ERROR] Failed to run git: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
