#!/usr/bin/env python
"""
Benchmark Task Runner
Executes a single benchmark task command, enforces timeouts, captures outputs, and verifies created artifacts.
"""
import os
import sys
import time
import subprocess
import json
import argparse
import shlex

def run_task(task_id, name, command, timeout=30, expected_exit_code=0, expected_artifacts=None):
    """
    Executes a task command as a subprocess, records metrics, and checks artifacts.
    """
    if expected_artifacts is None:
        expected_artifacts = []
        
    print(f"[RUN TASK] Executing '{name}' (ID: {task_id})...")
    print(f"[RUN TASK] Command: {command}")
    
    # Check if we should use the current python interpreter to avoid venv mismatches
    cmd_parts = shlex.split(command)
    if cmd_parts and cmd_parts[0] == "python":
        cmd_parts[0] = sys.executable
        
    start_time = time.time()
    
    try:
        # Run command with timeout
        res = subprocess.run(
            cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=True if os.name == 'nt' else False
        )
        elapsed = time.time() - start_time
        exit_code = res.returncode
        stdout = res.stdout
        stderr = res.stderr
        timeout_triggered = False
    except subprocess.TimeoutExpired as te:
        elapsed = time.time() - start_time
        exit_code = -1
        stdout = te.stdout or ""
        stderr = te.stderr or f"Timeout of {timeout}s expired."
        timeout_triggered = True
    except Exception as e:
        elapsed = time.time() - start_time
        exit_code = -1
        stdout = ""
        stderr = f"Execution failed: {str(e)}"
        timeout_triggered = False

    # Verify artifacts
    artifact_results = []
    artifacts_success = True
    for artifact in expected_artifacts:
        exists = os.path.exists(artifact)
        if not exists:
            artifacts_success = False
        artifact_results.append({
            "file": artifact,
            "exists": exists
        })
        
    exit_code_success = (exit_code == expected_exit_code) and not timeout_triggered
    success = exit_code_success and artifacts_success
    
    result = {
        "task_id": task_id,
        "name": name,
        "command": command,
        "exit_code": exit_code,
        "expected_exit_code": expected_exit_code,
        "elapsed_seconds": elapsed,
        "timeout_seconds": timeout,
        "timeout_triggered": timeout_triggered,
        "artifacts_checked": artifact_results,
        "exit_code_success": exit_code_success,
        "artifacts_success": artifacts_success,
        "success": success,
        "stdout_snippet": stdout[-1000:] if stdout else "",
        "stderr_snippet": stderr[-1000:] if stderr else ""
    }
    
    print(f"[RUN TASK] Finished '{name}' - Success: {success} (Elapsed: {elapsed:.2f}s, Exit Code: {exit_code})")
    if not exit_code_success:
        print(f"[RUN TASK] WARNING: Exit code {exit_code} did not match expected {expected_exit_code}")
    if not artifacts_success:
        missing = [a["file"] for a in artifact_results if not a["exists"]]
        print(f"[RUN TASK] WARNING: Missing expected artifacts: {', '.join(missing)}")
        
    return result

def main():
    parser = argparse.ArgumentParser(description="Run a single benchmark task")
    parser.add_argument("--task_id", type=str, required=True, help="Task ID")
    parser.add_argument("--name", type=str, default="", help="Task human-readable name")
    parser.add_argument("--command", type=str, required=True, help="Command to run")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--expected_exit_code", type=int, default=0, help="Expected exit code")
    parser.add_argument("--expected_artifacts", type=str, default="", help="Comma separated list of expected files")
    args = parser.parse_args()
    
    artifacts = [a.strip() for a in args.expected_artifacts.split(",") if a.strip()]
    name = args.name or args.task_id
    
    res = run_task(
        task_id=args.task_id,
        name=name,
        command=args.command,
        timeout=args.timeout,
        expected_exit_code=args.expected_exit_code,
        expected_artifacts=artifacts
    )
    
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["success"] else 1)

if __name__ == "__main__":
    main()
