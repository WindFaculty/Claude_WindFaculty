#!/usr/bin/env python
"""
Context Selector and Packer Script
Searches the workspace for relevant context files and formats selected context.

Supported engines:
  keyword  -- Simple keyword/substring scan (always available, no deps).
  semble   -- Semantic code search via MinishLab/semble (opt-in, pip package).
  auto     -- Prefer semble; fall back to keyword if semble unavailable/failing.

Usage:
  python scripts/context/select_context.py --query "CLAUDE" --engine auto
  python scripts/context/select_context.py --query "CLAUDE" --engine keyword
  python scripts/context/select_context.py --query "CLAUDE" --engine semble
"""
import sys
import os
import argparse
import re
import json
import datetime

# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def load_context_config(root: str = "."):
    """Load limits from configs/context.yaml."""
    config_path = os.path.join(root, "configs", "context.yaml")
    if not os.path.exists(config_path):
        return 20, []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        max_files = 20
        limit_match = re.search(r"max_files_selected:\s*(\d+)", content)
        if limit_match:
            max_files = int(limit_match.group(1))

        exclude = []
        exclude_match = re.search(
            r"exclude_patterns:\s*\n((?:\s*-\s*\"[^\"]+\"\s*\n?)+)", content
        )
        if exclude_match:
            for pat in re.findall(r'-\s*"([^"]+)"', exclude_match.group(1)):
                exclude.append(pat.replace("**/", "").replace("/**", ""))
        return max_files, exclude
    except Exception:
        return 20, []


def load_semble_config(root: str = "."):
    """Load Semble settings from configs/context.yaml."""
    config_path = os.path.join(root, "configs", "context.yaml")
    if not os.path.exists(config_path):
        return False, 10

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        enable = True
        semble_section = re.search(r"semble:\s*\n((?:\s+.*\n?)+)", content)
        if semble_section:
            sec_text = semble_section.group(1)
            enable_match = re.search(
                r"enable:\s*(true|false)", sec_text, re.IGNORECASE
            )
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


def load_engines_config(root: str = "."):
    """Load engine preference from configs/context.yaml engines section."""
    config_path = os.path.join(root, "configs", "context.yaml")
    defaults = {"default": "auto", "preferred": "semble", "fallback": "keyword"}
    if not os.path.exists(config_path):
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        engines_section = re.search(r"engines:\s*\n((?:\s+.*\n?)+)", content)
        if engines_section:
            sec = engines_section.group(1)
            for key in ("default", "preferred", "fallback"):
                m = re.search(rf'{key}:\s*"([^"]+)"', sec)
                if m:
                    defaults[key] = m.group(1)
        return defaults
    except Exception:
        return defaults


# ---------------------------------------------------------------------------
# Keyword engine
# ---------------------------------------------------------------------------

def search_files(query: str, exclude_patterns: list, root: str = ".") -> list:
    """Walk through repository files and search for the query string."""
    results = []
    target_exts = (".py", ".md", ".json", ".yaml", ".yml")
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [
            d for d in dirs
            if d not in exclude_patterns and not d.startswith(".")
        ]
        for file in files:
            if not file.endswith(target_exts):
                continue
            filepath = os.path.relpath(os.path.join(dirpath, file), root)
            if "artifacts" in filepath or "reports" in filepath:
                continue
            try:
                with open(
                    os.path.join(dirpath, file), "r", encoding="utf-8", errors="ignore"
                ) as f:
                    content = f.read()
                if query.lower() in content.lower():
                    matches = len(re.findall(re.escape(query), content, re.IGNORECASE))
                    results.append((filepath, matches))
            except Exception:
                pass
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def run_keyword_engine(query: str, max_files: int, exclude: list, root: str = ".") -> dict:
    """Run the keyword engine and return a normalised result dict."""
    matches = []
    if query:
        print(
            f"[CONTEXT SELECTOR] Scanning files for pattern "
            f"(standard keyword search): '{query}'"
        )
        matches = search_files(query, exclude, root)

    selected = []
    for filepath, count in matches[:max_files]:
        selected.append(
            {
                "file": filepath,
                "reason": f"Matches query '{query}' with {count} occurrence(s).",
                "relevance_score": count,
                "source": "keyword",
            }
        )

    if not selected:
        for file in ["CLAUDE.md", "README.md", "configs/tools.yaml"]:
            full = os.path.join(root, file) if root != "." else file
            if os.path.exists(full):
                selected.append(
                    {
                        "file": file,
                        "reason": "Fallback essential system configuration file.",
                        "relevance_score": 1,
                        "source": "keyword",
                    }
                )

    candidates = [
        {"file": fp, "relevance_score": c, "source": "keyword"}
        for fp, c in matches
    ]

    return {
        "engine": "keyword",
        "available": True,
        "fallback_used": False,
        "query": query,
        "selected": selected,
        "candidates": candidates,
        "metadata": {
            "upstream_commit": None,
            "mode": "builtin",
            "command": None,
        },
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Semble engine (via adapter)
# ---------------------------------------------------------------------------

def _import_adapter(root: str = "."):
    """Import semble_adapter from scripts/context/, injecting path if needed."""
    parent_dir = os.path.abspath(root)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from scripts.context.semble_adapter import (
        is_semble_available,
        run_semble_context_selection,
        get_semble_version_or_commit,
    )
    return is_semble_available, run_semble_context_selection, get_semble_version_or_commit


def run_semble_engine(query: str, max_files: int, root: str = ".") -> dict:
    """Run the Semble engine via the adapter."""
    try:
        is_available, run_selection, get_meta = _import_adapter(root)
    except ImportError as exc:
        return {
            "engine": "semble",
            "available": False,
            "fallback_used": False,
            "query": query,
            "selected": [],
            "candidates": [],
            "metadata": {"upstream_commit": None, "mode": "unknown", "command": None},
            "errors": [f"Could not import semble_adapter: {exc}"],
        }

    if not is_available():
        return {
            "engine": "semble",
            "available": False,
            "fallback_used": False,
            "query": query,
            "selected": [],
            "candidates": [],
            "metadata": {"upstream_commit": None, "mode": "package", "command": None},
            "errors": ['semble package not installed. Run: pip install "semble[mcp]"'],
        }

    print(
        f"[CONTEXT SELECTOR] Running Semble semantic code search for: '{query}'"
    )
    result = run_selection(query=query, max_files=max_files, root=root)
    return result


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def write_artifacts(
    result: dict,
    engine_requested: str,
    engine_used: str,
    fallback_used: bool,
    fallback_reason,
    root: str = ".",
):
    """Write all required artifact files."""
    artifacts_dir = os.path.join(root, "artifacts") if root != "." else "artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)

    selected = result.get("selected", [])
    candidates = result.get("candidates", [])
    query = result.get("query", "")

    # 1. context_candidates.json
    candidates_out = [
        {"file": c.get("file"), "relevance_score": c.get("relevance_score")}
        for c in candidates
    ]
    with open(os.path.join(artifacts_dir, "context_candidates.json"), "w", encoding="utf-8") as f:
        json.dump(candidates_out, f, indent=2)

    # 2. selected_context.json
    selected_out = [
        {
            "file": s.get("file"),
            "reason": s.get("reason"),
            "relevance_score": s.get("relevance_score"),
            "source": s.get("source", engine_used),
        }
        for s in selected
    ]
    with open(os.path.join(artifacts_dir, "selected_context.json"), "w", encoding="utf-8") as f:
        json.dump(selected_out, f, indent=2)

    # 3. context_pack.md
    with open(os.path.join(artifacts_dir, "context_pack.md"), "w", encoding="utf-8") as f:
        f.write("# Packed Active Context\n\n")
        f.write(f"Query keyword: `{query}`\n\n")
        f.write(f"Engine used: `{engine_used}`\n\n")
        if fallback_used:
            f.write(f"> ⚠️ Fallback activated: {fallback_reason}\n\n")
        f.write("## Selected Files\n\n")
        for item in selected:
            abs_path = os.path.abspath(item["file"])
            f.write(f"* **[{item['file']}](file:///{abs_path})**\n")
            f.write(f"  * Rationale: {item['reason']}\n")
            f.write(f"  * Relevance: {item['relevance_score']}\n\n")

    # 4. context_engine_metadata.json
    semble_meta = result.get("metadata", {})
    engine_metadata = {
        "engine_requested": engine_requested,
        "engine_used": engine_used,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "query": query,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "semble": {
            "available": result.get("available", False),
            "upstream_commit": semble_meta.get("upstream_commit"),
            "mode": semble_meta.get("mode", "unknown"),
        },
        "errors": result.get("errors", []),
    }
    with open(
        os.path.join(artifacts_dir, "context_engine_metadata.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(engine_metadata, f, indent=2)

    return selected, candidates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Assemble context files for Claude CLI"
    )
    parser.add_argument(
        "--query", type=str, default="", help="Keyword to search in workspace."
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "keyword", "semble"],
        default="auto",
        help=(
            "Context search engine. "
            "'keyword' = built-in scan. "
            "'semble' = Semble semantic search (must be installed). "
            "'auto' = prefer semble, fallback keyword."
        ),
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Max files to select (overrides configs/context.yaml).",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root path for searching and indexing.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 if the requested engine is unavailable.",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    max_files_cfg, exclude = load_context_config(root)
    max_files = args.max_files if args.max_files is not None else max_files_cfg

    engine_requested = args.engine
    engine_used = engine_requested
    fallback_used = False
    fallback_reason = None
    result = None

    # -----------------------------------------------------------------------
    # Engine dispatch
    # -----------------------------------------------------------------------

    if engine_requested == "keyword":
        result = run_keyword_engine(args.query, max_files, exclude, root)
        engine_used = "keyword"

    elif engine_requested == "semble":
        print("[CONTEXT SELECTOR] Engine=semble: strict mode — no fallback.")
        result = run_semble_engine(args.query, max_files, root)
        if not result.get("available") or result.get("errors"):
            err_msg = "; ".join(result.get("errors", ["Semble unavailable"]))
            print(
                f"[CONTEXT SELECTOR] [FAIL] Semble engine unavailable: {err_msg}",
                file=sys.stderr,
            )
            # Write metadata artifact even on failure for traceability
            write_artifacts(
                result,
                engine_requested="semble",
                engine_used="semble",
                fallback_used=False,
                fallback_reason=err_msg,
                root=root,
            )
            sys.exit(1)
        engine_used = "semble"

    elif engine_requested == "auto":
        # Try Semble first
        semble_result = run_semble_engine(args.query, max_files, root)
        if semble_result.get("available") and not semble_result.get("errors"):
            result = semble_result
            engine_used = "semble"
            print(
                f"[CONTEXT SELECTOR] Semble retrieved "
                f"{len(result.get('selected', []))} relevant files."
            )
        else:
            err_detail = "; ".join(
                semble_result.get("errors", ["Semble unavailable"])
            )
            fallback_reason = f"Semble unavailable/failed: {err_detail}"
            fallback_used = True
            print(
                f"[CONTEXT SELECTOR] Semble unavailable "
                f"({err_detail}). Falling back to keyword engine."
            )
            result = run_keyword_engine(args.query, max_files, exclude, root)
            result["fallback_used"] = True
            engine_used = "keyword"

    # -----------------------------------------------------------------------
    # Write artifacts
    # -----------------------------------------------------------------------
    selected, _ = write_artifacts(
        result,
        engine_requested=engine_requested,
        engine_used=engine_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        root=root,
    )

    print(
        f"[CONTEXT SELECTOR] Engine={engine_used} | "
        f"Packed {len(selected)} files in artifacts/selected_context.json"
    )
    if fallback_used:
        print(
            f"[CONTEXT SELECTOR] NOTE: fallback_used=true. "
            f"Reason: {fallback_reason}"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
