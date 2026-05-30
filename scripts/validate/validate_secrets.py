#!/usr/bin/env python
"""
Workspace Secret Leak Scanner
Scans staged changes and codebases for passwords or API tokens.
"""
import os
import sys
import re
import json

DEFAULT_PATTERNS = [
    r"(?i)(?:api[-_]?key|secret|password|token)\s*[:=]\s*[\"'][a-zA-Z0-9_\-\.]{12,}[\"']",
    r"sk-[A-Za-z0-9]{48}"
]

def load_secret_patterns():
    """Load secret regexes from configs/validation.yaml if available."""
    cfg_path = os.path.join("configs", "validation.yaml")
    if not os.path.exists(cfg_path):
        return DEFAULT_PATTERNS
        
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Locate the secrets section and extract its list items
        secrets_match = re.search(r"secrets:\s*\n((?:\s*-\s*\"[^\"]+\".*\n?)+)", content)
        if secrets_match:
            patterns = re.findall(r'-\s*"([^"]+)"', secrets_match.group(1))
            if patterns:
                # Unescape double backslashes in YAML representation
                return [p.replace("\\\\", "\\") for p in patterns]
    except Exception:
        pass
    return DEFAULT_PATTERNS

def scan_file(filepath, patterns):
    """Scan a single file for credential leaks."""
    leaks = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                # Skip comments or obvious placeholders
                if "your_" in line or "placeholder" in line or "example" in line:
                    continue
                for pat in patterns:
                    match = re.search(pat, line)
                    if match:
                        leaks.append((idx, line.strip()[:60]))
                        break
    except Exception:
        pass
    return leaks

def main():
    patterns = load_secret_patterns()
    print(f"[SECURITY CHECK] Scanning workspace files with {len(patterns)} patterns...")
    
    leaks_found = {}
    target_exts = (".py", ".json", ".yaml", ".yml", ".env")
    
    for root, dirs, files in os.walk("."):
        # Prune common ignored folders
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "artifacts", "reports", "third_party")]
        
        for file in files:
            if not file.endswith(target_exts):
                continue
            filepath = os.path.relpath(os.path.join(root, file), ".")
            if filepath == ".env.example":
                continue
                
            leaks = scan_file(filepath, patterns)
            if leaks:
                leaks_found[filepath] = leaks
                
    # Save validation report
    os.makedirs("artifacts", exist_ok=True)
    report = {
        "passed": len(leaks_found) == 0,
        "leaks": leaks_found
    }
    with open(os.path.join("artifacts", "security_validation.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    if leaks_found:
        print("[FAIL] CRITICAL: Potential secret key leak detected!")
        for file, occurrences in leaks_found.items():
            print(f"  File: {file}")
            for line_no, content in occurrences:
                print(f"    Line {line_no}: {content}")
        sys.exit(1)
        
    print("[PASS] Security scan passed. No credentials exposed in workspace files.")
    sys.exit(0)

if __name__ == "__main__":
    main()
