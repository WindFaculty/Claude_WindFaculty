#!/usr/bin/env python3
"""
Semble Local Search Wrapper Utility
Provides an interface to initialize index and query semantic search using MinishLab/semble.
"""
import os
import sys
import argparse
import json
import subprocess

def check_semble_available():
    """Verify if the `semble` package is importable in Python."""
    try:
        import semble
        return True, "semble package is available."
    except ImportError:
        return False, (
            "semble package is not installed.\n"
            "Please run bootstrap scripts or execute:\n"
            "  pip install \"semble[mcp]\""
        )

def run_semble_search(query, top_k=10, path="."):
    """Initialize Semble index and query local repository semantic search."""
    is_ok, msg = check_semble_available()
    if not is_ok:
        return {"error": msg, "results": []}

    try:
        from semble import SembleIndex
        
        # Resolve absolute path to ensure accuracy
        abs_path = os.path.abspath(path)
        
        # Semble automatically uses .sembleignore and .gitignore from the path root
        index = SembleIndex.from_path(abs_path)
        
        # Perform query
        search_results = index.search(query, top_k=top_k)
        
        formatted_results = []
        for r in search_results:
            chunk = getattr(r, "chunk", None)
            score = getattr(r, "score", 0.0)
            
            if chunk:
                file_path = getattr(chunk, "file_path", "")
                content = getattr(chunk, "content", "")
                start_line = getattr(chunk, "start_line", 1)
                end_line = getattr(chunk, "end_line", 1)
                
                # Make relative to base path
                if os.path.isabs(file_path):
                    rel_file = os.path.relpath(file_path, abs_path)
                else:
                    rel_file = file_path
                    
                formatted_results.append({
                    "file": rel_file.replace("\\", "/"),
                    "score": float(score),
                    "start_line": int(start_line),
                    "end_line": int(end_line),
                    "content": content
                })
        return {"error": None, "results": formatted_results}
    except Exception as e:
        return {"error": f"An error occurred during Semble search execution: {str(e)}", "results": []}

def main():
    parser = argparse.ArgumentParser(description="Semble Local Code Context Search Wrapper")
    parser.add_argument("--query", type=str, default="", help="Semantic search query keyword or phrase.")
    parser.add_argument("--top-k", type=int, default=10, help="Maximum number of context files to retrieve.")
    parser.add_argument("--path", type=str, default=".", help="Root path of repository to search.")
    parser.add_argument("--health-check", action="store_true", help="Verify if Semble is installed and operational.")
    args = parser.parse_args()

    if args.health_check:
        available, msg = check_semble_available()
        if available:
            print("[PASS] Semble wrapper verified. Library is importable.")
            sys.exit(0)
        else:
            print(f"[FAIL] {msg}")
            sys.exit(1)

    if not args.query:
        print("Error: --query parameter is required unless --health-check is used.", file=sys.stderr)
        sys.exit(1)

    output = run_semble_search(args.query, top_k=args.top_k, path=args.path)
    print(json.dumps(output, indent=2))
    
    if output["error"]:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
