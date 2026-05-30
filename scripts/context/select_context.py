#!/usr/bin/env python
"""
Context Selector and Packer Script
Searches the workspace for relevant context files and formats selected context.
"""
import sys
import os
import argparse
import re
import json

def load_context_config():
    """Load limits from configs/context.yaml."""
    config_path = os.path.join("configs", "context.yaml")
    if not os.path.exists(config_path):
        return 20, []
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Basic parsing
        max_files = 20
        limit_match = re.search(r"max_files_selected:\s*(\d+)", content)
        if limit_match:
            max_files = int(limit_match.group(1))
            
        exclude = []
        exclude_match = re.search(r"exclude_patterns:\s*\n((?:\s*-\s*\"[^\"]+\"\s*\n?)+)", content)
        if exclude_match:
            for pat in re.findall(r'-\s*"([^"]+)"', exclude_match.group(1)):
                exclude.append(pat.replace("**/", "").replace("/**", ""))
        return max_files, exclude
    except Exception:
        return 20, []

def search_files(query, exclude_patterns):
    """Walk through repository files and search for the query string."""
    results = []
    
    # Simple regex query search in source files
    target_exts = (".py", ".md", ".json", ".yaml", ".yml")
    for root, dirs, files in os.walk("."):
        # Prune excluded dirs
        dirs[:] = [d for d in dirs if d not in exclude_patterns and not d.startswith(".")]
        
        for file in files:
            if not file.endswith(target_exts):
                continue
                
            filepath = os.path.relpath(os.path.join(root, file), ".")
            # Avoid picking generated artifacts
            if "artifacts" in filepath or "reports" in filepath:
                continue
                
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if query.lower() in content.lower():
                    # Count occurrences
                    matches = len(re.findall(re.escape(query), content, re.IGNORECASE))
                    results.append((filepath, matches))
            except Exception:
                pass
                
    # Sort by relevance (match count) descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def main():
    parser = argparse.ArgumentParser(description="Assemble context files for Claude CLI")
    parser.add_argument("--query", type=str, default="", help="Keyword to search in workspace.")
    args = parser.parse_args()
    
    max_files, exclude = load_context_config()
    
    print(f"[CONTEXT SELECTOR] Scanning files for pattern: '{args.query}'")
    matches = search_files(args.query, exclude) if args.query else []
    
    selected = []
    # Cap at budget limit
    for filepath, count in matches[:max_files]:
        selected.append({
            "file": filepath,
            "reason": f"Matches query '{args.query}' with {count} occurrence(s).",
            "relevance_score": count
        })
        
    # If no matches, fall back to core files
    if not selected:
        for file in ["CLAUDE.md", "README.md", "configs/tools.yaml"]:
            if os.path.exists(file):
                selected.append({
                    "file": file,
                    "reason": "Fallback essential system configuration file.",
                    "relevance_score": 1
                })
                
    # Write selected context json
    os.makedirs("artifacts", exist_ok=True)
    with open(os.path.join("artifacts", "selected_context.json"), "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)
        
    # Write context pack markdown
    with open(os.path.join("artifacts", "context_pack.md"), "w", encoding="utf-8") as f:
        f.write("# Packed Active Context\n\n")
        f.write(f"Query keyword: `{args.query}`\n\n")
        f.write("## Selected Files\n\n")
        for item in selected:
            f.write(f"* **[{item['file']}](file:///{os.path.abspath(item['file'])})**\n")
            f.write(f"  * Rationale: {item['reason']}\n")
            f.write(f"  * Relevance: {item['relevance_score']}\n\n")
            
    print(f"[CONTEXT SELECTOR] Packed {len(selected)} files in artifacts/selected_context.json")

if __name__ == "__main__":
    main()
