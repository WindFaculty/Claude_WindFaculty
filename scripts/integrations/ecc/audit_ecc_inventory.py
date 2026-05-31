#!/usr/bin/env python3
import os
import json
from pathlib import Path

def main():
    vendor_dir = Path("third_party/everything-claude-code")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    inventory = {
        "SAFE_TO_COPY": [],
        "NEEDS_REVIEW": [],
        "DO_NOT_ENABLE_YET": []
    }

    # Define directories to scan
    scan_dirs = ["agents", "skills", "commands", "rules", "hooks", "mcp-configs", "contexts"]

    for d in scan_dirs:
        target_path = vendor_dir / d
        if not target_path.exists():
            continue

        for root, dirs, files in os.walk(target_path):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(vendor_dir)
                rel_path_str = str(rel_path).replace("\\", "/")

                # Categorization logic
                category = "NEEDS_REVIEW" # Default fallback

                if rel_path_str.startswith("agents/"):
                    category = "SAFE_TO_COPY"
                elif rel_path_str.startswith("commands/"):
                    category = "SAFE_TO_COPY"
                elif rel_path_str.startswith("rules/"):
                    category = "SAFE_TO_COPY"
                elif rel_path_str.startswith("mcp-configs/"):
                    category = "DO_NOT_ENABLE_YET"
                elif rel_path_str.startswith("skills/"):
                    skill_name = rel_path.parts[1] if len(rel_path.parts) > 1 else ""
                    safe_skills = [
                        "coding-standards",
                        "backend-patterns",
                        "tdd-workflow",
                        "security-review",
                        "verification-loop",
                        "eval-harness"
                    ]
                    if skill_name in safe_skills:
                        category = "SAFE_TO_COPY"
                    elif skill_name in ["continuous-learning", "strategic-compact", "clickhouse-io", "frontend-patterns", "project-guidelines-example"]:
                        category = "NEEDS_REVIEW"
                elif rel_path_str.startswith("hooks/") or rel_path_str.startswith("scripts/hooks/"):
                    category = "NEEDS_REVIEW"
                elif rel_path_str.startswith("contexts/"):
                    category = "NEEDS_REVIEW"

                inventory[category].append(rel_path_str)

    # Sort inventories for consistency
    for cat in inventory:
        inventory[cat].sort()

    # Save to JSON
    json_report = reports_dir / "ecc_inventory_20260531.json"
    with open(json_report, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)

    # Save to Markdown
    md_report = reports_dir / "ecc_inventory_20260531.md"
    with open(md_report, "w", encoding="utf-8") as f:
        f.write("# Everything Claude Code Integration Inventory Audit\n\n")
        f.write("This inventory categorizes all components of `everything-claude-code` for project-level selective migration.\n\n")
        
        for cat in ["SAFE_TO_COPY", "NEEDS_REVIEW", "DO_NOT_ENABLE_YET"]:
            f.write(f"## {cat}\n\n")
            if cat == "SAFE_TO_COPY":
                f.write("These files are safe to copy into the `.claude/` directory and can be loaded directly.\n\n")
            elif cat == "NEEDS_REVIEW":
                f.write("These files require active verification, runtime checks, or adapter bridging. Do not automate blindly.\n\n")
            elif cat == "DO_NOT_ENABLE_YET":
                f.write("These configurations present token budget or security risks (e.g. active MCP servers). They are locked by default.\n\n")

            f.write("| File Path | Status |\n")
            f.write("| --- | --- |\n")
            for item in inventory[cat]:
                f.write(f"| `third_party/everything-claude-code/{item}` | {cat} |\n")
            f.write("\n")

    print("ECC Inventory Audit completed successfully.")

if __name__ == "__main__":
    main()
