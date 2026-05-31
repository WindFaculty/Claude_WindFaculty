#!/usr/bin/env python3
import os
import re
from pathlib import Path

def main():
    agents_dir = Path(".claude/agents")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    report_lines = [
        "# Agent Model Audit & Remediation Report\n",
        "This report audits all agent templates in `.claude/agents/` for model configurations and explains the remediation steps applied to avoid excessive token costs (e.g., default `opus` models).\n\n",
        "## Audit Findings\n\n",
        "| Agent File | Original Model Setting | Action Taken |\n",
        "| --- | --- | --- |\n"
    ]

    remediated_count = 0

    if agents_dir.exists():
        for file_path in agents_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find model setting
            model_match = re.search(r"^model:\s*([^\r\n]+)", content, re.MULTILINE)
            if model_match:
                original_model = model_match.group(1).strip()
                # Comment out or remove the model line to inherit default model safely
                # Replacing 'model: x' with '# model: x (commented out to inherit default)'
                new_content = re.sub(
                    r"^model:\s*[^\r\n]+",
                    f"# model: {original_model} (commented out to inherit default)",
                    content,
                    flags=re.MULTILINE
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                report_lines.append(f"| `{file_path.name}` | `{original_model}` | Commented out to inherit default model |\n")
                remediated_count += 1
            else:
                report_lines.append(f"| `{file_path.name}` | *None (Inherits Default)* | No action needed |\n")

    report_lines.append(f"\nTotal agents remediated: {remediated_count}\n")
    report_lines.append("\n## Recommendation Policy\n")
    report_lines.append("- All specialist subagents have had `model: opus` commented out.\n")
    report_lines.append("- By commenting this setting out, they will automatically inherit the default active model of the Claude CLI session, keeping cost-efficiency optimized.\n")

    # Save to markdown report
    report_file = reports_dir / "ecc_agent_models_20260531.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.writelines(report_lines)

    print(f"Agent model audit completed. Remediated {remediated_count} agents.")

if __name__ == "__main__":
    main()
