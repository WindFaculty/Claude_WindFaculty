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

def load_semble_config():
    """Load Semble settings from configs/context.yaml."""
    config_path = os.path.join("configs", "context.yaml")
    if not os.path.exists(config_path):
        return False, 10
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        enable = True
        # Match "semble:" section
        semble_section = re.search(r"semble:\s*\n((?:\s+.*\n?)+)", content)
        if semble_section:
            sec_text = semble_section.group(1)
            enable_match = re.search(r"enable:\s*(true|false)", sec_text, re.IGNORECASE)
            if enable_match:
                enable = enable_match.group(1).lower() == "true"
            top_k = 10
            top_k_match = re.search(r"top_k:\s*(\d+)", sec_text)
            if top_k_match:
                top_k = int(top_k_match.group(1))
            return enable, top_k
        return False, 10
    except Exception:
        return False, 10

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
    semble_enable, semble_top_k = load_semble_config()
    
    using_semble = False
    matches = []
    
    if args.query and semble_enable:
        try:
            # Insert the parent folder to path to make sure scripts folder is visible if run standalone
            parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                
            from scripts.tools.semble_search import check_semble_available, run_semble_search
            available, _ = check_semble_available()
            if available:
                print(f"[CONTEXT SELECTOR] Performing semantic code search using Semble for: '{args.query}'")
                search_res = run_semble_search(args.query, top_k=semble_top_k)
                if not search_res.get("error"):
                    raw_matches = search_res.get("results", [])
                    file_scores = {}
                    for r in raw_matches:
                        file_path = r["file"]
                        score = r["score"]
                        file_scores[file_path] = max(file_scores.get(file_path, 0.0), score)
                    
                    matches = [(f, int(s * 100)) for f, s in file_scores.items()]
                    matches.sort(key=lambda x: x[1], reverse=True)
                    using_semble = True
                    print(f"[CONTEXT SELECTOR] Semble retrieved {len(matches)} relevant files.")
                else:
                    print(f"[CONTEXT SELECTOR] Semble search error: {search_res['error']}. Falling back...")
        except Exception as e:
            print(f"[CONTEXT SELECTOR] Failed invoking Semble: {str(e)}. Falling back to standard keyword scanner.")
            
    if not using_semble and args.query:
        print(f"[CONTEXT SELECTOR] Scanning files for pattern (standard keyword search): '{args.query}'")
        matches = search_files(args.query, exclude)
        
    selected = []
    # Cap at budget limit
    for filepath, count in matches[:max_files]:
        if using_semble:
            reason = f"Semble semantic search match for '{args.query}' with confidence score {count/100:.2f}."
        else:
            reason = f"Matches query '{args.query}' with {count} occurrence(s)."
            
        selected.append({
            "file": filepath,
            "reason": reason,
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
                
    # Write context candidates
    candidates = []
    for filepath, count in matches:
        candidates.append({
            "file": filepath,
            "relevance_score": count
        })
        
    os.makedirs("artifacts", exist_ok=True)
    with open(os.path.join("artifacts", "context_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    # Write selected context json
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
