#!/usr/bin/env python
"""
Repository Structure Footprint Summarizer
Walks the codebase, counts file statistics by extension, and logs structural metadata.
"""
import os
import sys
import json
import time

def calculate_footprint():
    print("[SUMMARIZER] Inspecting workspace footprint and directory layout...")
    start_time = time.time()
    
    exclude_dirs = ["node_modules", "__pycache__", ".git", "build", "dist", ".pytest_cache", ".venv", "third_party"]
    
    stats = {
        "total_files": 0,
        "total_size_bytes": 0,
        "extensions": {}
    }
    
    structure = []
    
    for root, dirs, files in os.walk("."):
        # Prune ignored folders
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        
        for file in files:
            filepath = os.path.relpath(os.path.join(root, file), ".")
            if "artifacts" in filepath or "reports" in filepath:
                continue
                
            try:
                size = os.path.getsize(filepath)
                stats["total_files"] += 1
                stats["total_size_bytes"] += size
                
                ext = os.path.splitext(file)[1].lower() or "no_extension"
                stats["extensions"][ext] = stats["extensions"].get(ext, 0) + 1
                
                if total_files_limit := stats["total_files"] <= 200: # Limit depth detail in JSON
                    structure.append({
                        "file": filepath,
                        "size_bytes": size,
                        "ext": ext
                    })
            except Exception:
                pass
                
    elapsed = time.time() - start_time
    
    os.makedirs("artifacts", exist_ok=True)
    summary_path = os.path.join("artifacts", "repo_structure_summary.json")
    
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 3),
        "footprint": stats,
        "files_detailed": structure
    }
    
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[SUMMARIZER] Successfully analyzed {stats['total_files']} files ({stats['total_size_bytes']} bytes footprint).")
        print(f"[SUMMARIZER] Output structure details written at: {summary_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Footprint summarizer failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = calculate_footprint()
    sys.exit(0 if success else 1)
