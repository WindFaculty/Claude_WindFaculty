#!/usr/bin/env python3
"""
Semble Context Backend Adapter
================================
Thin adapter between Claude_WindFaculty context selection and the upstream
MinishLab/semble package (https://github.com/MinishLab/semble).

This module NEVER crashes select_context.py when Semble is unavailable.
It provides:
  - is_semble_available() -> bool
  - get_semble_version_or_commit() -> dict
  - run_semble_context_selection(query, max_files, root) -> dict

Output schema is normalised to the internal standard defined in
integrations/semble/manifest.yaml.

Integration mode: package
Install: pip install "semble[mcp]"
Upstream commit recorded in: integrations/semble/manifest.yaml
"""

import os
import sys
import importlib
import importlib.metadata


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UPSTREAM_URL = "https://github.com/MinishLab/semble"
UPSTREAM_COMMIT = "ea3c9180bd7b8c3ae2133120b17c3599ac93dec3"
INTEGRATION_MODE = "package"


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def is_semble_available() -> bool:
    """Return True if the semble Python package can be imported."""
    try:
        import semble  # noqa: F401
        return True
    except ImportError:
        return False


def get_semble_version_or_commit() -> dict:
    """
    Return metadata about the installed semble package.

    Returns:
        dict with keys: available (bool), version (str|None),
        upstream_commit (str), mode (str), install_hint (str)
    """
    available = is_semble_available()
    version = None
    if available:
        try:
            version = importlib.metadata.version("semble")
        except importlib.metadata.PackageNotFoundError:
            version = None

    return {
        "available": available,
        "version": version,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_url": UPSTREAM_URL,
        "mode": INTEGRATION_MODE,
        "install_hint": 'pip install "semble[mcp]"',
    }


# ---------------------------------------------------------------------------
# Core selection
# ---------------------------------------------------------------------------

def run_semble_context_selection(
    query: str,
    max_files: int = 10,
    root: str = ".",
) -> dict:
    """
    Run Semble semantic context selection for the given query.

    Args:
        query:     Search query string.
        max_files: Maximum number of files to return in selected[].
        root:      Root directory for the Semble index. Defaults to CWD.

    Returns:
        Normalised result dict conforming to internal schema:
        {
          "engine": "semble",
          "available": bool,
          "fallback_used": false,
          "query": str,
          "selected": [{file, reason, relevance_score, source}, ...],
          "candidates": [{file, relevance_score, source}, ...],
          "metadata": {upstream_commit, mode, command},
          "errors": [str, ...]
        }

    On failure:
        Returns dict with available=False (or fallback_used=True) and errors[].
        Does NOT raise exceptions — callers handle the fallback.
    """
    meta = get_semble_version_or_commit()
    base_result = {
        "engine": "semble",
        "available": meta["available"],
        "fallback_used": False,
        "query": query,
        "selected": [],
        "candidates": [],
        "metadata": {
            "upstream_commit": UPSTREAM_COMMIT,
            "mode": INTEGRATION_MODE,
            "command": None,
        },
        "errors": [],
    }

    if not meta["available"]:
        base_result["errors"].append(
            f"semble package not installed. Run: {meta['install_hint']}"
        )
        return base_result

    if not query or not query.strip():
        base_result["errors"].append("query is empty; no Semble search performed.")
        return base_result

    try:
        # Delegate to the existing thin wrapper (scripts/tools/semble_search.py)
        # to keep search logic DRY and avoid duplication.
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from scripts.tools.semble_search import run_semble_search

        abs_root = os.path.abspath(root)
        search_res = run_semble_search(query, top_k=max_files * 3, path=abs_root)

        if search_res.get("error"):
            base_result["errors"].append(search_res["error"])
            return base_result

        raw_results = search_res.get("results", [])

        # Aggregate scores by file (take max across chunks)
        file_scores: dict[str, float] = {}
        for r in raw_results:
            fp = r.get("file", "")
            score = float(r.get("score", 0.0))
            if fp:
                file_scores[fp] = max(file_scores.get(fp, 0.0), score)

        # Build candidates list (all files, sorted by score)
        candidates = [
            {
                "file": fp,
                "relevance_score": round(score, 4),
                "source": "semble",
            }
            for fp, score in sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        ]
        base_result["candidates"] = candidates

        # Build selected list (top max_files)
        selected = []
        for item in candidates[:max_files]:
            selected.append(
                {
                    "file": item["file"],
                    "reason": (
                        f"Semble semantic search match for '{query}' "
                        f"with confidence score {item['relevance_score']:.4f}."
                    ),
                    "relevance_score": item["relevance_score"],
                    "source": "semble",
                }
            )
        base_result["selected"] = selected

        return base_result

    except Exception as exc:  # pragma: no cover — defensive
        base_result["errors"].append(f"Semble execution error: {exc}")
        return base_result


# ---------------------------------------------------------------------------
# CLI entry-point (health check / quick smoke test)
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Semble Adapter — health check and context selection"
    )
    parser.add_argument("--health-check", action="store_true",
                        help="Print availability status and exit.")
    parser.add_argument("--query", type=str, default="",
                        help="Run context selection for this query.")
    parser.add_argument("--max-files", type=int, default=10,
                        help="Max files to select.")
    parser.add_argument("--root", type=str, default=".",
                        help="Root path for Semble indexing.")
    args = parser.parse_args()

    if args.health_check:
        info = get_semble_version_or_commit()
        print(json.dumps(info, indent=2))
        sys.exit(0 if info["available"] else 1)

    if not args.query:
        print("Error: --query is required unless --health-check is used.", file=sys.stderr)
        sys.exit(1)

    result = run_semble_context_selection(
        query=args.query,
        max_files=args.max_files,
        root=args.root,
    )
    print(json.dumps(result, indent=2))
    if result["errors"] or not result["available"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
