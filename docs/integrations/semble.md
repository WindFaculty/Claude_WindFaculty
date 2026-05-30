# Semble Integration Guide

> **Integration Status:** Semble is vendored as a **pip package** (not source-vendored).
> The adapter provides graceful fallback to keyword search when Semble is unavailable.

---

## What is Semble?

[Semble](https://github.com/MinishLab/semble) is a **fast, offline code search tool** built by MinishLab that uses semantic embeddings to find relevant code chunks in a repository. It runs entirely on CPU, requires no external API keys, and uses ~98% fewer tokens than grep+read approaches.

In Claude_WindFaculty, Semble serves as the **preferred context selection backend** for `select_context.py`. When Semble is available, it performs semantic search over repository files instead of simple keyword substring matching.

---

## Upstream Reference

| Field | Value |
|---|---|
| **Upstream URL** | https://github.com/MinishLab/semble |
| **Upstream Commit** | `ea3c9180bd7b8c3ae2133120b17c3599ac93dec3` |
| **Commit Date** | 2026-05-29 |
| **License** | MIT |
| **Integration Mode** | Python package (`pip install "semble[mcp]"`) |
| **Integration Manifest** | `integrations/semble/manifest.yaml` |

---

## Why Semble Instead of Writing It Ourselves?

1. **Upstream quality:** Semble uses optimised CPU-only embedding models tested across real codebases.
2. **No reinvention:** Writing semantic embedding + indexing from scratch is thousands of lines of work; using the upstream package keeps the repo focused on its mission (environment/tooling around Claude Code).
3. **License compatibility:** MIT license allows integration without restriction.
4. **Offline/private:** No data leaves the machine.

---

## Integration Architecture

```
scripts/context/select_context.py
  └─► (engine=semble) → scripts/context/semble_adapter.py
                              └─► scripts/tools/semble_search.py
                                        └─► semble (pip package)

  └─► (engine=keyword) → built-in search_files() [always available]

  └─► (engine=auto) → try semble → fallback keyword if unavailable
```

---

## Installation

Semble is **not installed by default** — it is opt-in.

```bash
pip install "semble[mcp]"
```

For MCP server integration with Claude Code CLI:
```bash
uvx --from "semble[mcp]" semble
```

---

## Usage

### Keyword engine (always available, no dependencies):
```bash
python scripts/context/select_context.py --query "context selector" --engine keyword
```

### Semble engine (requires semble installed, strict mode):
```bash
python scripts/context/select_context.py --query "context selector" --engine semble
```

> If Semble is not installed, this exits with code 1 and does NOT fall back.

### Auto engine (recommended, prefers Semble, falls back to keyword):
```bash
python scripts/context/select_context.py --query "context selector" --engine auto
```

### Additional options:
```bash
python scripts/context/select_context.py \
  --query "context selector" \
  --engine auto \
  --max-files 15 \
  --root . \
  --strict
```

---

## Output Artifacts

All runs produce these artifacts in `artifacts/`:

| File | Contents |
|---|---|
| `context_candidates.json` | All files found, ranked by relevance |
| `selected_context.json` | Top N selected files with reasons |
| `context_pack.md` | Human-readable context summary |
| `context_engine_metadata.json` | Which engine was used, fallback status, Semble commit |

### `context_engine_metadata.json` schema:
```json
{
  "engine_requested": "auto",
  "engine_used": "keyword",
  "fallback_used": true,
  "fallback_reason": "Semble unavailable/failed: semble package not installed.",
  "query": "CLAUDE",
  "timestamp": "2026-05-31T00:00:00Z",
  "semble": {
    "available": false,
    "upstream_commit": "ea3c9180bd7b8c3ae2133120b17c3599ac93dec3",
    "mode": "package"
  },
  "errors": ["semble package not installed. Run: pip install \"semble[mcp]\""]
}
```

---

## Fallback Behavior

The `--engine auto` mode is designed to be **transparent and honest**:

1. It attempts to use Semble first.
2. If Semble is unavailable (not installed, crashes, etc.), it falls back to keyword search.
3. `fallback_used: true` is **always** written to `context_engine_metadata.json` when fallback occurs.
4. The reason is written to `fallback_reason` — never hidden.

> ⚠️ **Never claim Semble ran if `fallback_used: true`.** Always check `context_engine_metadata.json`.

---

## Semble Adapter API

`scripts/context/semble_adapter.py` provides:

```python
from scripts.context.semble_adapter import (
    is_semble_available,       # -> bool
    get_semble_version_or_commit,  # -> dict
    run_semble_context_selection,  # -> dict (normalised schema)
)
```

The adapter never raises exceptions — it returns structured error dicts for callers to handle.

---

## Known Limitations

1. **Semble not installed in default environment:** Until `pip install "semble[mcp]"` is run, all `--engine auto` calls will use keyword fallback.
2. **Index build time:** First Semble run on a large repository may take a few seconds to build the index.
3. **`.sembleignore`:** Files listed in `.sembleignore` are excluded from Semble indexing (see root `.sembleignore`).
4. **Not a perfect AST tool:** Semble uses embedding-based semantic search, not true AST parsing. Do not claim AST-precision for Semble results.

---

## Updating Semble Upstream

To upgrade to a newer Semble version:

1. Check the upstream commit: `https://github.com/MinishLab/semble/commits/main`
2. Update `integrations/semble/manifest.yaml`:
   - `upstream_commit: "<new SHA>"`
   - `upstream_commit_date: "<new date>"`
   - `imported_at: "<new UTC timestamp>"`
3. Update the pinned version in `requirements.txt` or `pyproject.toml` if using one.
4. Update `scripts/context/semble_adapter.py` constant `UPSTREAM_COMMIT`.
5. Run tests: `python -m pytest -q`
6. Run smoke test: `python scripts/context/select_context.py --query "CLAUDE" --engine auto`
7. Record a new report in `reports/`.

---

## Tests

| Test File | What It Covers |
|---|---|
| `tests/test_semble_adapter.py` | Adapter availability, schema, error handling |
| `tests/test_select_context_engines.py` | Engine dispatch, fallback, artifacts, safe_bash |
| `tests/test_semble_integration.py` | Legacy wrapper compatibility |
