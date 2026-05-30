#!/usr/bin/env python
"""
Workspace Context Compactor & Token Saver
Reads selected context files and strips comments, docstrings, and whitespaces to optimize tokens.
"""
import os
import sys
import re
import json

def load_compression_settings():
    """Reads compact settings from configs/context.yaml."""
    yaml_path = os.path.join("configs", "context.yaml")
    enabled = True
    level = "medium"
    
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            enable_match = re.search(r"enable_compactor:\s*(true|false)", content, re.IGNORECASE)
            if enable_match:
                enabled = enable_match.group(1).lower() == "true"
                
            level_match = re.search(r"compact_level:\s*\"?([a-zA-Z]+)\"?", content)
            if level_match:
                level = level_match.group(1).lower()
        except Exception:
            pass
            
    return enabled, level

def strip_python_comments_and_docstrings(source_code, compact_level="medium"):
    """
    Strips single line comments, docstrings, and redundant whitespaces.
    Matches Claw-compactor profiles.
    """
    # 1. Strip Docstrings (multi-line triple-quoted strings)
    # Simple regex match for triple quotes
    cleaned = re.sub(r'r?\"\"\"[\s\S]*?\"\"\"', '', source_code)
    cleaned = re.sub(r"r?\'\'\'[\s\S]*?\'\'\'", '', cleaned)
    
    # 2. Strip single line comments
    if compact_level in ("medium", "high"):
        # Match '#' unless it's inside quotes
        lines = []
        for line in cleaned.splitlines():
            # Basic comment strip (ignores quote boundary cases simply)
            line_stripped = line.split('#', 1)[0].rstrip()
            if compact_level == "high" and not line_stripped:
                continue # Skip completely empty lines
            lines.append(line_stripped)
        cleaned = "\n".join(lines)
        
    # 3. Strip extra spaces / blank lines
    if compact_level == "high":
        # Remove consecutive blank lines
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        
    return cleaned

def compress_context():
    print("[COMPACTOR] Executing context compression pipeline...")
    enabled, level = load_compression_settings()
    
    if not enabled:
        print("[COMPACTOR] Context compaction disabled by configs/context.yaml. Skipping.")
        return True

    selected_json = os.path.join("artifacts", "selected_context.json")
    if not os.path.exists(selected_json):
        print("[WARNING] Selected context JSON not found. Run select_context.py first.")
        return False
        
    try:
        with open(selected_json, "r", encoding="utf-8") as f:
            selected_files = json.load(f)
            
        print(f"[COMPACTOR] Compact level: {level}. Processing {len(selected_files)} files...")
        
        comp_md_path = os.path.join("artifacts", "context_pack_compressed.md")
        
        saved_bytes_total = 0
        original_bytes_total = 0
        
        with open(comp_md_path, "w", encoding="utf-8") as out:
            out.write("# Packed Context (Claw-Compacted)\n\n")
            out.write(f"Compression parameters: level=`{level}`\n\n")
            
            for item in selected_files:
                filepath = item["file"]
                if not os.path.exists(filepath):
                    continue
                    
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    original_content = f.read()
                    
                orig_bytes = len(original_content)
                original_bytes_total += orig_bytes
                
                # Apply surgical compactor only to python source files
                if filepath.endswith(".py"):
                    compressed_content = strip_python_comments_and_docstrings(original_content, level)
                else:
                    compressed_content = original_content
                    
                comp_bytes = len(compressed_content)
                saved_bytes = orig_bytes - comp_bytes
                saved_bytes_total += saved_bytes
                
                out.write(f"## File: `{filepath}` (Saved: {saved_bytes} bytes)\n\n")
                out.write("```python\n")
                out.write(compressed_content)
                out.write("\n```\n\n")
                
        pct = (saved_bytes_total / original_bytes_total * 100) if original_bytes_total > 0 else 0
        print(f"[COMPACTOR] Compacted successfully! Saved {saved_bytes_total} / {original_bytes_total} bytes ({pct:.1f}% space saved)")
        print(f"[COMPACTOR] Output saved to: {comp_md_path}")
        
        # Save compact stats artifact
        stats = {
            "original_bytes": original_bytes_total,
            "compressed_bytes": original_bytes_total - saved_bytes_total,
            "saved_bytes": saved_bytes_total,
            "savings_percentage": round(pct, 2)
        }
        with open(os.path.join("artifacts", "context_budget.json"), "w", encoding="utf-8") as sf:
            json.dump(stats, sf, indent=2)
            
        return True
    except Exception as e:
        print(f"[ERROR] Context compaction failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = compress_context()
    sys.exit(0 if success else 1)
