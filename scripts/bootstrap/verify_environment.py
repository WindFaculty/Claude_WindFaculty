#!/usr/bin/env python
"""
Environment Verification Script
Checks Python, git, claude, config integrity, and secret leaks.
"""
import sys
import os
import subprocess
import re
import json

def check_python_version():
    """Verify python is at least version 3.8."""
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) < (3, 8):
        return False, f"Python {major}.{minor} detected. Minimum required is 3.8."
    return True, f"Python {major}.{minor} is valid."

def check_git():
    """Verify git command availability."""
    try:
        res = subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if res.returncode == 0:
            return True, res.stdout.strip()
        return False, "git exists but returned non-zero exit code."
    except Exception as e:
        return False, f"git command not found: {str(e)}"

def check_claude_cli():
    """Verify Claude CLI (claude command) availability."""
    try:
        # Check if claude CLI runs. Sometimes 'claude --version' is slow, so we can check if it exists in path or returns quickly
        res = subprocess.run(["claude", "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if res.returncode == 0 or "claude" in res.stdout.lower() or "claude" in res.stderr.lower():
            return True, res.stdout.strip() or "claude CLI available"
        
        # Fallback to checking --version
        res2 = subprocess.run(["claude", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if res2.returncode == 0:
            return True, res2.stdout.strip()
            
        return False, "claude command returned non-zero exit code or is a placeholder."
    except Exception as e:
        # Check standard paths or return a warning
        return False, f"claude command not found in environment PATH: {str(e)}"

def check_required_directories():
    """Verify essential directories exist."""
    required = ["configs", "scripts", ".claude", "tests", "artifacts", "reports", "benchmarks"]
    missing = []
    for d in required:
        if not os.path.exists(d):
            missing.append(d)
    if missing:
        return False, f"Missing required directories: {', '.join(missing)}"
    return True, "All required directories exist."

def simple_yaml_parse(filepath):
    """
    Very basic YAML parser to validate yaml structure without requiring PyYAML.
    Tries PyYAML first, falls back to basic structural parser.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Try using pyyaml if installed
    try:
        import yaml
        yaml.safe_load(content)
        return True
    except ImportError:
        pass
    
    # Fallback line-by-line syntax check
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # Check basic key-value pattern: "key: value" or "key:"
        if ":" not in line_stripped:
            return False
            
    return True

def check_configs():
    """Parse key config files to check structural validity."""
    configs = [
        "configs/tools.yaml",
        "configs/budgets.yaml",
        "configs/context.yaml",
        "configs/validation.yaml",
        "configs/benchmark.yaml",
        ".claude/settings.json",
        ".mcp.json"
    ]
    invalid = []
    for cfg in configs:
        if not os.path.exists(cfg):
            invalid.append(f"{cfg} (Missing)")
            continue
        
        try:
            if cfg.endswith('.json'):
                with open(cfg, 'r', encoding='utf-8') as f:
                    json.load(f)
            else:
                if not simple_yaml_parse(cfg):
                    invalid.append(f"{cfg} (Invalid YAML structure)")
        except Exception as e:
            invalid.append(f"{cfg} (Error: {str(e)})")
            
    if invalid:
        return False, f"Config validation failures: {', '.join(invalid)}"
    return True, "All configuration files parsed successfully."

def check_env_secrets():
    """Scan workspace for committed .env keys or secrets."""
    # 1. Check if .env is tracked in git
    is_tracked = False
    try:
        res = subprocess.run(["git", "ls-files", ".env"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if ".env" in res.stdout:
            is_tracked = True
    except Exception:
        pass
        
    if is_tracked:
        return False, "CRITICAL: .env file is tracked in git! Please remove it from git tracking immediately."
        
    # 2. Check if .env exists and contains realistic secret values
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if "CLAUDE_API_KEY" in line or "API_KEY" in line:
                    match = re.search(r'=\s*([^\s#]+)', line)
                    if match:
                        val = match.group(1)
                        if val and "your_" not in val and "placeholder" not in val and len(val) > 10:
                            return False, f"CRITICAL: Found realistic key in .env: {line.split('=')[0].strip()} = {val[:4]}... [Blocked committed secret risk]"
        except Exception as e:
            return False, f"Failed reading .env file: {str(e)}"
            
    return True, "No committed .env secrets or git-tracked .env files detected."

def main():
    print("=========================================")
    print("Claude WindFaculty Environment Verifier")
    print("=========================================")
    
    checks = [
        ("Python Version", check_python_version),
        ("Git Availability", check_git),
        ("Claude CLI Status", check_claude_cli),
        ("Workspace Directories", check_required_directories),
        ("Config Files Parse", check_configs),
        ("Secret Exposure Scan", check_env_secrets)
    ]
    
    all_pass = True
    results = {}
    
    for label, fn in checks:
        passed, msg = fn()
        status = "PASS" if passed else "WARNING/FAIL"
        print(f"[{status}] {label}: {msg}")
        results[label] = {"passed": passed, "message": msg}
        # Only strictly fail on critical issues: python version, directories, configs, secrets
        if not passed and label in ["Python Version", "Workspace Directories", "Config Files Parse", "Secret Exposure Scan"]:
            all_pass = False
            
    print("=========================================")
    if all_pass:
        print("RESULT: ENVIRONMENT SECURE & VERIFIED")
        sys.exit(0)
    else:
        print("RESULT: ENVIRONMENTAL ERRORS DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    main()
