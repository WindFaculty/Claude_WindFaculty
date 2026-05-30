#!/usr/bin/env python
"""
Benchmark Suite Runner
Loads a suite configuration, executes all tasks sequentially, scores them,
logs results, and generates a formatted execution summary report.
"""
import os
import sys
import time
import json
import argparse
from datetime import datetime

# Insert current dir to sys.path to easily load local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from scripts.benchmark.run_task import run_task
from scripts.benchmark.score_run import score_task, load_scoring_config

def parse_suite_yaml(file_path):
    """
    Zero-dependency parser for smoke.yaml.
    Reliably extracts tasks and attributes even without PyYAML.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Suite config not found: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    data = {"tasks": []}
    current_task = None
    in_tasks = False
    in_artifacts = False
    
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
            
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            
            # Remove matching quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
                
            if key == "name" and not in_tasks:
                data["name"] = val
            elif key == "description" and not in_tasks:
                data["description"] = val
            elif key == "tasks":
                in_tasks = True
                continue
                
            if in_tasks:
                if key.startswith("-"):
                    if current_task:
                        data["tasks"].append(current_task)
                    key = key.replace("-", "").strip()
                    current_task = {key: val, "expected_artifacts": []}
                    in_artifacts = False
                elif current_task:
                    if key == "expected_artifacts":
                        in_artifacts = True
                    else:
                        in_artifacts = False
                        if val.isdigit():
                            current_task[key] = int(val)
                        else:
                            current_task[key] = val
        else:
            if stripped.startswith("-") and in_artifacts and current_task:
                artifact = stripped.replace("-", "").strip()
                if (artifact.startswith('"') and artifact.endswith('"')) or (artifact.startswith("'") and artifact.endswith("'")):
                    artifact = artifact[1:-1]
                current_task["expected_artifacts"].append(artifact)
                
    if current_task:
        data["tasks"].append(current_task)
        
    return data

def render_box_line(text, width=78, align="left"):
    if align == "center":
        return f"| {text.center(width - 4)} |"
    return f"| {text.ljust(width - 4)} |"

def print_premium_terminal_summary(suite_name, total_tasks, passed_tasks, elapsed, avg_score, results):
    """Prints a premium ASCII table showing benchmark results."""
    width = 80
    border = "-" * (width - 2)
    
    print(f"+{border}+")
    print(render_box_line(f"CLAUDE_WINDFACULTY BENCHMARK RUNNER", width, "center"))
    print(render_box_line(f"Suite: {suite_name.upper()} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", width, "center"))
    print(f"+{border}+")
    
    header = f"{'Task ID'.ljust(20)} | {'Verdict'.ljust(8)} | {'Time'.ljust(7)} | {'Acc'.ljust(5)} | {'Speed'.ljust(5)} | {'Score'.ljust(6)}"
    print(render_box_line(header, width))
    print(f"+{border}+")
    
    for r in results:
        t_id = r["task_id"][:19]
        verdict = "PASS" if r["success"] else "FAIL"
        time_str = f"{r['elapsed_seconds']:.2f}s"
        acc = f"{r['scores']['accuracy']:.0f}"
        spd = f"{r['scores']['speed']:.0f}"
        final = f"{r['scores']['final']:.1f}%"
        
        line_text = f"{t_id.ljust(20)} | {verdict.ljust(8)} | {time_str.rjust(7)} | {acc.rjust(5)} | {spd.rjust(5)} | {final.rjust(6)}"
        print(render_box_line(line_text, width))
        
    print(f"+{border}+")
    summary1 = f"Total Tasks: {total_tasks} | Passed: {passed_tasks} | Failed: {total_tasks - passed_tasks}"
    summary2 = f"Total Elapsed Time: {elapsed:.2f}s | Average Suite Score: {avg_score:.1f}%"
    print(render_box_line(summary1, width, "center"))
    print(render_box_line(summary2, width, "center"))
    print(f"+{border}+")

def generate_markdown_report(suite_name, suite_desc, total_tasks, passed_tasks, elapsed, avg_score, results, report_path):
    """Generates a premium markdown report documenting the benchmark suite run."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    content = f"""# Benchmark Suite Execution Report

## Overview
* **Benchmark Suite**: `{suite_name}`
* **Description**: {suite_desc}
* **Run Timestamp**: `{timestamp}`
* **Overall Verdict**: **{"PASS" if passed_tasks == total_tasks else "FAIL_WITH_WARNINGS"}**

## Performance Summary
* **Average Suite Score**: `{avg_score:.1f}%`
* **Total Tasks Executed**: `{total_tasks}`
* **Tasks Passed**: `{passed_tasks}`
* **Tasks Failed**: `{total_tasks - passed_tasks}`
* **Total Duration**: `{elapsed:.2f} seconds`

---

## Detailed Task Results

| Task ID | Verdict | Execution Time | Accuracy Score | Speed Score | Efficiency Score | Final Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    
    for r in results:
        verdict = "✅ PASS" if r["success"] else "❌ FAIL"
        scores = r["scores"]
        content += f"| `{r['task_id']}` | {verdict} | `{r['elapsed_seconds']:.2f}s` | `{scores['accuracy']}%` | `{scores['speed']}%` | `{scores['token_efficiency']}%` | **`{scores['final']}%`** |\n"
        
    content += """
---

## Key Highlights & Observations
"""
    
    if avg_score >= 90.0:
        content += "> [!TIP]\n> **Excellent Performance**: The active workspace components operate well within safe limits, demonstrating exceptional speed, accuracy, and correct artifact generations.\n\n"
    elif avg_score >= 70.0:
        content += "> [!NOTE]\n> **Stable Execution**: Workspace functions are reliable. Speed scores could be improved slightly to optimize execution efficiency.\n\n"
    else:
        content += "> [!WARNING]\n> **Performance Degraded**: Significant failures or timeouts were logged during this benchmark. Review the corresponding validation logs immediately.\n\n"
        
    content += f"""## Execution Trace Audit
All raw JSON traces are persisted locally inside:
`benchmarks/results/`

*Report compiled automatically by Claude_WindFaculty Benchmark Suite Runner.*
"""
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Run Claude_WindFaculty benchmark suite")
    parser.add_argument("--suite", type=str, default="smoke", help="Suite identifier (default: smoke)")
    args = parser.parse_args()
    
    suite_file = os.path.join("benchmarks", "suites", f"{args.suite}.yaml")
    if not os.path.exists(suite_file):
        print(f"[ERROR] Suite configuration not found: {suite_file}")
        sys.exit(1)
        
    try:
        suite_data = parse_suite_yaml(suite_file)
    except Exception as e:
        print(f"[ERROR] Failed parsing suite yaml: {str(e)}")
        sys.exit(1)
        
    suite_name = suite_data.get("name", args.suite)
    suite_desc = suite_data.get("description", "")
    tasks = suite_data.get("tasks", [])
    
    print(f"[BENCHMARK] Starting Suite '{suite_name}' with {len(tasks)} tasks.")
    
    results = []
    start_suite_time = time.time()
    passed_tasks = 0
    
    scoring_weights = load_scoring_config()
    
    for t in tasks:
        task_id = t["task_id"]
        name = t.get("name", task_id)
        command = t.get("command", "")
        timeout = t.get("timeout", 30)
        expected_exit_code = t.get("expected_exit_code", 0)
        expected_artifacts = t.get("expected_artifacts", [])
        
        # Execute the task
        task_res = run_task(
            task_id=task_id,
            name=name,
            command=command,
            timeout=timeout,
            expected_exit_code=expected_exit_code,
            expected_artifacts=expected_artifacts
        )
        
        # Score the task
        scored = score_task(task_res, scoring_weights)
        results.append(scored)
        
        if scored["success"]:
            passed_tasks += 1
            
    elapsed_suite_time = time.time() - start_suite_time
    total_tasks = len(tasks)
    avg_score = sum(r["scores"]["final"] for r in results) / total_tasks if total_tasks > 0 else 0.0
    
    # Print Unicode CLI Box
    print_premium_terminal_summary(suite_name, total_tasks, passed_tasks, elapsed_suite_time, avg_score, results)
    
    # Save unified JSON execution log
    results_dir = os.path.join("benchmarks", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = int(start_suite_time)
    results_json_path = os.path.join(results_dir, f"run_{suite_name}_{timestamp}.json")
    
    suite_results = {
        "suite": suite_name,
        "description": suite_desc,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "elapsed_seconds": elapsed_suite_time,
        "total_tasks": total_tasks,
        "passed_tasks": passed_tasks,
        "failed_tasks": total_tasks - passed_tasks,
        "average_score": avg_score,
        "tasks": results
    }
    
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(suite_results, f, indent=2)
        
    print(f"[BENCHMARK] Detailed JSON results saved to: {results_json_path}")
    
    # Generate premium Markdown report
    report_filename = f"benchmark_{suite_name}_{timestamp}.md"
    report_path = os.path.join("reports", report_filename)
    generate_markdown_report(suite_name, suite_desc, total_tasks, passed_tasks, elapsed_suite_time, avg_score, results, report_path)
    print(f"[BENCHMARK] Premium markdown report written to: {report_path}")
    
    # Exit with 0 if all tasks passed, otherwise 1
    sys.exit(0 if passed_tasks == total_tasks else 1)

if __name__ == "__main__":
    main()
