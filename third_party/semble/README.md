# third_party/semble

Semble is managed as a **pip package**, not a vendored source snapshot.

## Integration Mode: Package

Install command:
```
pip install "semble[mcp]"
```

MCP server CLI (for Claude Code integration):
```
uvx --from "semble[mcp]" semble
```

## Why not vendored?

- The pip package is stable, versioned, and updateable via standard tooling.
- Vendoring the full source would copy 5,000+ lines of ML embedding code without adding value.
- The `integrations/semble/manifest.yaml` records the upstream commit SHA for full traceability.

## Upgrading

1. Update `integrations/semble/manifest.yaml` with new upstream commit SHA.
2. Pin the new version in `requirements.txt` or `pyproject.toml`.
3. Run `python -m pytest -q` to verify no regressions.

## References

- Upstream: https://github.com/MinishLab/semble
- License: MIT
- Recorded at commit: `ea3c9180bd7b8c3ae2133120b17c3599ac93dec3`
