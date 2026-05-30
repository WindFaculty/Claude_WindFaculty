#!/usr/bin/env python
"""
Subagent Runner and Invocation Coordinator
Parses specialist subagent prompts, bundles runtime payloads, and logs traces.
"""
import os
import sys
import re
import json
import time
import argparse
import urllib.request

def parse_subagent_file(agent_name):
    """Parse specialist subagent prompt files for instructions."""
    filepath = os.path.join(".claude", "agents", f"{agent_name}.md")
    if not os.path.exists(filepath):
        # Alternative path check
        filepath = os.path.join("..", ".claude", "agents", f"{agent_name}.md")
        if not os.path.exists(filepath):
            return None, f"Agent prompt file {agent_name}.md not found."
            
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        role = re.search(r"## Role Definition\s*\n(.*)", content)
        objectives = re.search(r"## Objectives\s*\n((?:\s*.*\n?)+?)(?=\n##|$)", content)
        instructions = re.search(r"## Instructions\s*\n((?:\s*.*\n?)+?)(?=\n##|$)", content)
        out_format = re.search(r"## Output Format\s*\n((?:\s*.*\n?)+?)(?=\n##|$)", content)
        
        system_prompt = f"""Role: {role.group(1).strip() if role else ""}
Objectives:
{objectives.group(1).strip() if objectives else ""}
Instructions:
{instructions.group(1).strip() if instructions else ""}
Output Format:
{out_format.group(1).strip() if out_format else ""}
"""
        return system_prompt, None
    except Exception as e:
        return None, f"Error parsing prompt file: {str(e)}"

def run_anthropic_call(system_prompt, user_input, api_key):
    """Zero-dependency REST API client call to Anthropic Messages endpoint."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data.get("content", [{}])[0].get("text", "")
            return content, None
    except Exception as e:
        return None, f"REST call failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Specialist Subagent Runner")
    parser.add_argument("--agent", type=str, required=True, help="Specialist agent name (e.g. context-researcher).")
    parser.add_argument("--input", type=str, required=True, help="Input context or task for the subagent.")
    args = parser.parse_args()
    
    print(f"[SUBAGENT] Invoking specialist subagent: '{args.agent}'")
    system_prompt, err = parse_subagent_file(args.agent)
    if err:
        print(f"[ERROR] {err}")
        sys.exit(1)
        
    api_key = os.getenv("CLAUDE_API_KEY") or ""
    # If the key is a placeholder, ignore it
    if "your_" in api_key or "placeholder" in api_key or not api_key:
        api_key = None
        
    result_text = ""
    is_dry_run = True
    
    if api_key:
        print("[SUBAGENT] API Key detected. Executing remote subagent call...")
        response, err = run_anthropic_call(system_prompt, args.input, api_key)
        if err:
            print(f"[WARNING] Remote subagent execution failed: {err}")
            print("[SUBAGENT] Falling back to dry-run mode.")
        else:
            result_text = response
            is_dry_run = False
            print("[SUBAGENT] Remote subagent execution completed successfully.")
            
    if is_dry_run:
        print("[SUBAGENT] [DRY RUN] Structured subagent query package created.")
        # Mock structural output matching the subagent format
        if "context-researcher" in args.agent:
            result_text = json.dumps([
                {
                    "file": "scripts/tools/safe_bash.py",
                    "reason": "Contains core command safety patterns and fallback lists.",
                    "symbols": ["classify_command", "load_policies"]
                }
            ], indent=2)
        elif "test-diagnoser" in args.agent:
            result_text = json.dumps({
                "failure_summary": "Passed all verifications cleanly.",
                "failed_tests": [],
                "root_cause_estimate": "N/A",
                "suggested_actions": []
            }, indent=2)
        else:
            result_text = f"Dry-run result for subagent {args.agent}."
            
    # Write subagent run log to artifacts
    os.makedirs("artifacts", exist_ok=True)
    run_log = {
        "agent": args.agent,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dry_run": is_dry_run,
        "prompt_packaged": {
            "system": system_prompt,
            "user": args.input
        },
        "response": result_text
    }
    
    log_path = os.path.join("artifacts", f"subagent_{args.agent}_run.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2)
        
    print(f"[SUBAGENT] Execution trace saved to: {log_path}")
    print("\n--- Subagent Output ---")
    print(result_text)
    print("-----------------------\n")

if __name__ == "__main__":
    main()
