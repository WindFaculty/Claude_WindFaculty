#!/usr/bin/env python
"""
Safe Test Execution Wrapper
Runs test suites securely, captures outputs, and logs validation data.
"""
import sys
import os
import subprocess
import json

def main():
    print("[TEST RUNNER] Initializing safe test execution...")
    
    # Run pytest and capture results
    pytest_cmd = ["python", "-m", "pytest", "-v"]
    if len(sys.argv) > 1:
        pytest_cmd.extend(sys.argv[1:])
        
    try:
        res = subprocess.run(pytest_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        exit_code = res.returncode
        
        # Save results to artifacts directory
        os.makedirs("artifacts", exist_ok=True)
        results = {
            "exit_code": exit_code,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "command": " ".join(pytest_cmd)
        }
        
        with open(os.path.join("artifacts", "test_validation.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        print(f"[TEST RUNNER] Finished with exit code: {exit_code}")
        print(res.stdout)
        if res.stderr:
            print("Errors:")
            print(res.stderr)
            
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] Failed to run test runner: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
