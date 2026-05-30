# Third Party Repositories

This directory acts as a registry for mature, external open-source repositories integrated into the Claude operating environment. Rather than rebuilding mature code graph tools, semantic checkers, or shell filters, we vendor or clone them here.

## Cloned Repositories Manifest
All candidate repositories are registered in `third_party/manifest.yaml`. 

To clone the registered repositories without manually setting them up:
```bash
python scripts/bootstrap/clone_third_party.py
```

## Policy
1. Do not manually edit files inside cloned submodules.
2. Keep all third-party code excluded from the root repository commit steps via `.gitignore`.
