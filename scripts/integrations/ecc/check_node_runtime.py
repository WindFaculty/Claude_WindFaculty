#!/usr/bin/env python3
import subprocess
import os
import sys

def main():
    print("[CHECK] Starting Node.js and NPM Compatibility Check...")

    # Check node version
    try:
        node_version = subprocess.check_output("node --version", shell=True, text=True, encoding="utf-8").strip()
        print(f"[SUCCESS] Node.js is available: {node_version}")
    except Exception as e:
        print("[ERROR] Node.js is NOT available in this environment.")
        print(f"Details: {str(e)}")
        sys.exit(1)

    # Check npm version
    try:
        npm_version = subprocess.check_output("npm --version", shell=True, text=True, encoding="utf-8").strip()
        print(f"[SUCCESS] NPM is available: {npm_version}")
    except Exception as e:
        print("[WARNING] NPM is NOT available or failed to execute.")
        print(f"Details: {str(e)}")
        npm_version = "Unavailable"

    # Run internal tests
    test_script = os.path.join("third_party", "everything-claude-code", "tests", "run-all.js")
    tests_passed = False
    test_output = ""

    if os.path.exists(test_script):
        print(f"[CHECK] Executing vendored everything-claude-code tests: {test_script}")
        try:
            # Change directory to run the test script in its own context
            cwd = os.path.join("third_party", "everything-claude-code")
            res = subprocess.run("node tests/run-all.js", shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
            test_output = f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}"
            if res.returncode == 0:
                print("[SUCCESS] All vendored tests passed successfully.")
                tests_passed = True
            else:
                print(f"[WARNING] Vendored tests returned exit code {res.returncode}.")
        except Exception as e:
            print(f"[ERROR] Failed to run tests: {str(e)}")
            test_output = f"Exception: {str(e)}"
    else:
        print("[WARNING] Vendored tests run-all.js not found.")
        test_output = "No tests found."

    # Write compatibility report to reports directory
    os.makedirs("reports", exist_ok=True)
    report_path = os.path.join("reports", "ecc_node_compatibility_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Everything-Claude-Code Node.js Compatibility Report\n\n")
        f.write("## Runtime Environments\n\n")
        f.write(f"- **Node.js Version**: `{node_version}`\n")
        f.write(f"- **NPM Version**: `{npm_version}`\n")
        f.write(f"- **Operating System**: `{sys.platform}`\n\n")
        
        f.write("## Vendored Tests Execution\n\n")
        f.write(f"- **Command run**: `node tests/run-all.js` inside `third_party/everything-claude-code/`\n")
        f.write(f"- **Result**: `{'PASSED' if tests_passed else 'FAILED/SKIPPED'}`\n\n")
        f.write("### Execution Logs\n")
        f.write("```text\n")
        f.write(test_output)
        f.write("\n```\n")

    print(f"[CHECK] Node.js compatibility report saved to {report_path}")

if __name__ == "__main__":
    main()
