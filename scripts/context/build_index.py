#!/usr/bin/env python
"""
Workspace AST and Symbol Index Builder
Walks through repository source files, extracts symbol definitions, and writes cache logs.
"""
import os
import sys
import ast
import json
import time

def parse_python_symbols(filepath):
    """Parses a Python file using the native AST parser to extract symbols."""
    symbols = {
        "classes": [],
        "functions": [],
        "imports": []
    }
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        tree = ast.parse(content, filename=filepath)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            elif isinstance(node, ast.FunctionDef):
                # Avoid listing nested helper functions separately if they belong inside a class
                symbols["functions"].append({
                    "name": node.name,
                    "line": node.lineno
                })
            elif isinstance(node, ast.Import):
                for name in node.names:
                    symbols["imports"].append(name.name)
            elif isinstance(node, ast.ImportFrom):
                symbols["imports"].append(node.module or "")
                
        return symbols
    except Exception as e:
        return {"error": str(e)}

def build_index():
    print("[INDEXER] Initiating workspace AST symbol indexation...")
    start_time = time.time()
    
    # 1. Resolve limits and patterns from configs/context.yaml
    exclude_dirs = ["node_modules", "__pycache__", ".git", "build", "dist", ".pytest_cache", ".venv", "third_party"]
    
    index = {}
    total_files = 0
    
    # 2. Walk directory structure
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.relpath(os.path.join(root, file), ".")
                if "artifacts" in filepath or "reports" in filepath:
                    continue
                    
                symbols = parse_python_symbols(filepath)
                if "error" not in symbols:
                    index[filepath] = symbols
                    total_files += 1

    # 3. Save index cache JSON
    cache_dir = ".cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "symbol_index.json")
    
    index_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_files_indexed": total_files,
        "elapsed_seconds": round(time.time() - start_time, 3),
        "symbols": index
    }
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(index_payload, f, indent=2)
        print(f"[INDEXER] Successfully indexed {total_files} source files.")
        print(f"[INDEXER] Symbol cache saved at: {cache_path} (Elapsed: {index_payload['elapsed_seconds']}s)")
        return True
    except Exception as e:
        print(f"[ERROR] Failed writing symbol index cache: {str(e)}")
        return False

if __name__ == "__main__":
    success = build_index()
    sys.exit(0 if success else 1)
