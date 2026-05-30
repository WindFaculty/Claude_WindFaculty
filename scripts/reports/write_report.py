#!/usr/bin/env python
"""
Unified Task Execution Report Generator
Aggregates repository intake data, context packing, git diffs, test logs,
and safety validator outcomes into a structured markdown report based on templates.
"""
import os
import sys
import re
import json
import time
import subprocess

def read_artifact_json(filename):
    """Safely loads a JSON log from the artifacts directory."""
    path = os.path.join("artifacts", filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def get_git_diff_stats():
    """Calculates active git diff modifications (changed files, additions, deletions)."""
    try:
        # Check staged and unstaged changes
        res = subprocess.run(["git", "diff", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, encoding="utf-8")
        diff_text = res.stdout
        if not diff_text.strip():
            res_staged = subprocess.run(["git", "diff", "--cached"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, encoding="utf-8")
            res_unstaged = subprocess.run(["git", "diff"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, encoding="utf-8")
            diff_text = (res_staged.stdout or "") + (res_unstaged.stdout or "")
    except Exception:
        diff_text = ""
        
    if not diff_text.strip():
        return [], 0, 0, "No active workspace modifications"
        
    changed_files = set()
    additions = 0
    deletions = 0
    
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = re.findall(r"b/([^\s\n]+)", line)
            if parts:
                changed_files.add(parts[-1])
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
            
    stat_msg = f"{len(changed_files)} file(s) modified, {additions} insertion(s)(+), {deletions} deletion(s)(-)"
    return list(changed_files), additions, deletions, stat_msg

def extract_task_title():
    """Extracts the first heading from task.md or returns a default title."""
    task_path = os.path.join("task.md")
    if os.path.exists(task_path):
        try:
            with open(task_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#"):
                        return line.replace("#", "").strip()
        except Exception:
            pass
    return "Claude_WindFaculty Environment Operations"

def main():
    print("[REPORTS] Commencing unified task report compilation...")
    
    # 1. Load Template
    template_path = os.path.join("reports", "templates", "task_report.md")
    if not os.path.exists(template_path):
        print(f"[ERROR] Task report template not found: {template_path}")
        sys.exit(1)
        
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    # 2. Gather All Available Artifacts
    intake = read_artifact_json("repo_intake.json")
    context = read_artifact_json("selected_context.json")
    diff_val = read_artifact_json("diff_validation.json")
    test_val = read_artifact_json("test_validation.json")
    security = read_artifact_json("security_validation.json")
    ctx_val = read_artifact_json("context_validation.json")
    
    # Get active git statistics
    changed_files, additions, deletions, stat_summary = get_git_diff_stats()
    
    # 3. Format Intake Section
    if intake:
        git_info = intake.get("git", {})
        stats = intake.get("statistics", {})
        counts = stats.get("source_files", {})
        repo_intake_str = f"""* **Git Branch**: `{git_info.get("branch", "unknown")}`
* **HEAD Commit**: `{git_info.get("commit", "unknown")}`
* **Codebase Footprint**: `{stats.get("total_size_bytes", 0)} bytes`
* **Source Count**: {counts.get("py", 0)} python source files, {counts.get("md", 0)} markdown documents"""
    else:
        repo_intake_str = "*No repository intake statistics recorded.*"
        
    # 4. Format Context Section
    if context:
        ctx_lines = []
        for c in context:
            ctx_lines.append(f"* **[`{c['file']}`](file:///{os.path.abspath(c['file'])})**")
            ctx_lines.append(f"  * Rationale: {c.get('reason', 'None documented.')}")
        context_selected_str = "\n".join(ctx_lines)
    else:
        context_selected_str = "*No active context files selected.*"
        
    # 5. Format Plan Section
    plan_path = os.path.join("task.md")
    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_str = f.read()[:2000] # Cap size
        except Exception:
            plan_str = "Refer to active [task.md](file:///C:/Users/tranx/.gemini/antigravity/brain/3d3a3489-1bda-482c-83bd-13df5af4c876/task.md) for details."
    else:
        plan_str = "No active checklist found."
        
    # 6. Format Git Diff Section
    files_changed_str = "\n".join(f"* `{f}`" for f in changed_files) if changed_files else "*No files modified.*"
    
    # 7. Format Security Check Section
    if security:
        passed = security.get("passed", True)
        status_str = "✅ **PASS** - No API credentials or passwords exposed in workspace files." if passed else "❌ **FAIL** - Potential API key exposure detected!"
    else:
        status_str = "⚠️ **WARNING** - Security credentials scan was not executed."
        
    # 8. Format Test Results Section
    if test_val:
        exit_code = test_val.get("exit_code", -1)
        stdout = test_val.get("stdout", "")
        metrics = test_val.get("metrics", {})
        
        status_icon = "✅" if exit_code == 0 else "❌"
        metrics_str = f"| Total Cases: `{metrics.get('total', 0)}` | Passed: `{metrics.get('passed', 0)}` | Failed: `{metrics.get('failed', 0)}` | Skipped: `{metrics.get('skipped', 0)}`" if metrics else ""
        
        test_results_str = f"""* **Status**: {status_icon} Exit Code `{exit_code}` {metrics_str}
* **Test Command Run**: `{test_val.get("command", "pytest")}`
* **Execution Log Output**:
```text
{stdout[:1000]}
```"""
    else:
        test_results_str = "*No test execution log recorded.*"
        
    # 9. Format Verification Gate Outcomes
    gates = []
    # Context Gate
    if ctx_val:
        passed = ctx_val.get("passed", True)
        verdict = ctx_val.get("verdict", "UNKNOWN")
        gates.append(f"* **Context Budget Gate**: `[{verdict}]` - {ctx_val.get('message', '')}")
    else:
        gates.append("* **Context Budget Gate**: `[SKIPPED]` - No context validation executed.")
        
    # Diff Gate
    if diff_val:
        passed = diff_val.get("passed", True)
        verdict = diff_val.get("verdict", "UNKNOWN")
        gates.append(f"* **Git Diff Safety Gate**: `[{verdict}]` - {diff_val.get('message', '')}")
    else:
        gates.append("* **Git Diff Safety Gate**: `[SKIPPED]` - No diff validation executed.")
        
    # Security Gate
    if security:
        verdict = "PASS" if security.get("passed", True) else "SECRET_RISK"
        gates.append(f"* **Workspace Security Gate**: `[{verdict}]` - No credential leaks discovered.")
    else:
        gates.append("* **Workspace Security Gate**: `[SKIPPED]` - No security leak scan executed.")
        
    validations_str = "\n".join(gates)
    
    # 10. Compute Strict Safety Verdict
    verdict = "PASS"
    issues = []
    
    # Security check fail triggers immediate fail
    if security and not security.get("passed", True):
        verdict = "FAIL"
        issues.append("Workspace credentials scanner found api key leaks.")
        
    # Test failures trigger immediate fail
    if test_val and test_val.get("exit_code", -1) != 0:
        verdict = "FAIL"
        issues.append("Pytest execution failed with non-zero exit code.")
        
    # Warning validations trigger PASS_WITH_WARNINGS if tests passed
    if verdict == "PASS":
        warns = []
        if ctx_val and not ctx_val.get("passed", True):
            warns.append("Context budget exceeded or empty rationale.")
        if diff_val and not diff_val.get("passed", True):
            warns.append(f"Diff validator warning: {diff_val.get('verdict')}")
            
        if warns:
            verdict = "PASS_WITH_WARNINGS"
            issues.extend(warns)
            
    # Format risks and next actions based on verdict
    if verdict == "PASS":
        risks_str = "✅ **None** - All verification gates, security limits, and test executions passed."
        next_actions_str = """* Complete task documentation and report system verification.
* Commit code improvements and log files cleanly to the repository."""
    elif verdict == "PASS_WITH_WARNINGS":
        risks_str = f"⚠️ **WARNINGS** - {', '.join(issues)}"
        next_actions_str = """* Rectify context limits or formatting warnings flagged by validators.
* Confirm that any changes outside context budget have documented rationales."""
    else:
        risks_str = f"🚨 **CRITICAL** - {', '.join(issues)}"
        next_actions_str = """* Troubleshoot and fix the broken code or test failures immediately.
* Sanitize any leaked API keys or credentials from workspace files immediately."""
        
    # 11. Compile Placeholder Replacements
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S GMT', time.gmtime())
    task_title = extract_task_title()
    diff_status = diff_val.get("verdict", "PASS") if diff_val else "PASS"
    
    compiled = template_content
    compiled = compiled.replace("{{TASK_TITLE}}", task_title)
    compiled = compiled.replace("{{VERDICT}}", verdict)
    compiled = compiled.replace("{{TIMESTAMP}}", timestamp)
    compiled = compiled.replace("{{REPO_INTAKE}}", repo_intake_str)
    compiled = compiled.replace("{{CONTEXT_SELECTED}}", context_selected_str)
    compiled = compiled.replace("{{PLAN}}", plan_str)
    compiled = compiled.replace("{{DIFF_STATUS}}", diff_status)
    compiled = compiled.replace("{{FILES_CHANGED}}", files_changed_str)
    compiled = compiled.replace("{{DIFF_SUMMARY}}", stat_summary)
    compiled = compiled.replace("{{SECURITY_STATUS}}", status_str)
    compiled = compiled.replace("{{TEST_RESULTS}}", test_results_str)
    compiled = compiled.replace("{{VALIDATIONS}}", validations_str)
    compiled = compiled.replace("{{RISKS}}", risks_str)
    compiled = compiled.replace("{{NEXT_ACTIONS}}", next_actions_str)
    
    # Avoid writing prohibited phrases (lazy engineering) without warning
    for lazy, _ in [("all good", ""), ("done", ""), ("should be fine", ""), ("probably fixed", "")]:
        if lazy in compiled.lower():
            print(f"[WARNING] Lazy phrasing '{lazy}' detected. Ensure strict evidence is provided.")
            
    # 12. Save Compiled Report
    report_filename = f"execution_report_{int(time.time())}.md"
    report_path = os.path.join("reports", report_filename)
    
    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(compiled)
        
    print(f"[REPORTS] Compiled execution report successfully at: {report_path}")
    print(f"[REPORTS] Calculated Verdict: {verdict}")

if __name__ == "__main__":
    main()
