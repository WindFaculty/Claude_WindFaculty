#!/usr/bin/env python
"""
Repository Intake Automation Script
Gathers workspace statistics, Git metadata, and configuration integrity status.
"""
import os
import sys
import subprocess
import json
import time

def get_git_metadata():
    """Extract branch and commit metadata."""
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, shell=True).strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, shell=True).strip()
        author = subprocess.check_output(["git", "log", "-1", "--format=%an <%ae>"], text=True, shell=True).strip()
        return branch, commit, author
    except Exception:
        return "unknown", "unknown", "unknown"

def count_source_files():
    """Count code files present in the repository."""
    counts = {"py": 0, "md": 0, "yaml": 0, "json": 0}
    total_size = 0
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "artifacts", "reports", "third_party", ".venv")]
        for file in files:
            ext = file.split(".")[-1].lower()
            if ext in counts:
                counts[ext] += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, file))
                except Exception:
                    pass
    return counts, total_size

def main():
    print("[INTAKE] Commencing repository onboarding intake...")
    
    branch, commit, author = get_git_metadata()
    file_counts, total_bytes = count_source_files()
    
    intake_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "branch": branch,
            "commit": commit,
            "last_author": author
        },
        "statistics": {
            "source_files": file_counts,
            "total_size_bytes": total_bytes
        },
        "status": "ONBOARDED"
    }
    
    # Save artifacts/repo_intake.json
    os.makedirs("artifacts", exist_ok=True)
    with open(os.path.join("artifacts", "repo_intake.json"), "w", encoding="utf-8") as f:
        json.dump(intake_data, f, indent=2)
        
    # Save reports/repo_intake.md
    os.makedirs("reports", exist_ok=True)
    report_content = f"""# Repository Intake Report

* **Intake Time**: {time.strftime("%Y-%m-%d %H:%M:%S GMT", time.gmtime())}
* **Status**: {intake_data['status']}

## Git Workspace Metadata
* **Active Branch**: `{branch}`
* **HEAD Commit**: `{commit}`
* **Last Author**: `{author}`

## Workspace File Statistics
* **Python source files**: {file_counts['py']}
* **Markdown files**: {file_counts['md']}
* **YAML configurations**: {file_counts['yaml']}
* **JSON configurations**: {file_counts['json']}
* **Total code footprint**: {total_bytes} bytes

---
*Report compiled by repo_intake.py*
"""
    with open(os.path.join("reports", "repo_intake.md"), "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("[INTAKE] Finished. Created repo_intake.json and repo_intake.md.")

if __name__ == "__main__":
    main()
