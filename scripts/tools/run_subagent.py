#!/usr/bin/env python
"""
Subagent Runner and Invocation Coordinator
Parses specialist subagent prompts, bundles runtime payloads, and logs traces.
Now supports AWS Bedrock API provider routing, default Haiku 4.5, and Sonnet 4.6 escalation.
"""
import os
import sys
import re
import json
import time
import argparse
import urllib.request

# Ensure project root is in path for importing local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def load_dotenv():
    """Simple robust zero-dependency .env loader."""
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and val:
                        os.environ[key] = val
        except Exception:
            pass

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
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Specialist Subagent Runner")
    parser.add_argument("--agent", type=str, required=True, help="Specialist agent name (e.g. context-researcher).")
    parser.add_argument("--input", type=str, required=True, help="Input context or task for the subagent.")
    
    # Provider overrides and Routing options
    parser.add_argument("--provider", type=str, default=None, choices=["anthropic", "aws_bedrock"],
                        help="Override default provider.")
    parser.add_argument("--model", type=str, default=None,
                        help="Override default model alias (e.g., haiku_4_5).")
    parser.add_argument("--escalate-model", type=str, default=None,
                        help="Override default escalation model (e.g., sonnet_4_6).")
    parser.add_argument("--no-escalation", action="store_true",
                        help="Explicitly disable model escalation routing.")
    parser.add_argument("--force-sonnet", action="store_true",
                        help="Force direct execution on Claude Sonnet 4.6.")
    
    args = parser.parse_args()
    
    print(f"[SUBAGENT] Invoking specialist subagent: '{args.agent}'")
    system_prompt, err = parse_subagent_file(args.agent)
    if err:
        print(f"[ERROR] {err}")
        sys.exit(1)
        
    # Resolve provider config
    provider_name = args.provider or os.getenv("CLAUDE_PROVIDER") or "anthropic"
    
    result_text = ""
    is_dry_run = True
    active_model = "unknown"
    routing_info = None

    if provider_name == "aws_bedrock":
        print("[SUBAGENT] Using AWS Bedrock API provider. Evaluating routing policy...")
        
        # Imports routing and provider models
        from src.claude_agent.routing.model_policy import evaluate_routing_policy
        from src.claude_agent.providers.aws_bedrock import AwsBedrockClaudeProvider
        
        # Evaluate model routing policy rules
        force_haiku = (args.model == "haiku_4_5")
        routing_decision = evaluate_routing_policy(
            prompt_text=args.input,
            messages=[],
            agent_name=args.agent,
            force_sonnet=args.force_sonnet,
            force_haiku=force_haiku,
            no_escalation=args.no_escalation
        )
        
        routing_info = routing_decision
        active_model = routing_decision["selected_model"]
        print(f"[SUBAGENT] Routing Decision: Model selected: '{active_model}' (Escalated: {routing_decision['escalated']})")
        print(f"[SUBAGENT] Routing Reasons: {', '.join(routing_decision['reasons'])}")
        
        # Execute invocation via Bedrock Provider
        provider = AwsBedrockClaudeProvider()
        response, err = provider.complete(
            messages=[{"role": "user", "content": args.input}],
            system_prompt=system_prompt,
            model_alias=active_model
        )
        
        if err:
            print(f"[WARNING] AWS Bedrock call failed: {err}")
            print("[SUBAGENT] Falling back to dry-run mode.")
        else:
            result_text = response
            is_dry_run = False
            print("[SUBAGENT] AWS Bedrock execution completed successfully.")
            
    else:
        # Backward compatibility mode for native Anthropic endpoint
        print("[SUBAGENT] Using standard Anthropic API provider.")
        active_model = args.model or os.getenv("CLAUDE_DEFAULT_MODEL") or "claude-3-5-sonnet-20241022"
        api_key = os.getenv("CLAUDE_API_KEY") or ""
        
        # If the key is a placeholder, ignore it
        if "your_" in api_key or "placeholder" in api_key or not api_key:
            api_key = None
            
        if api_key:
            print("[SUBAGENT] Anthropic API Key detected. Executing remote subagent call...")
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
        "provider": provider_name,
        "model": active_model,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dry_run": is_dry_run,
        "prompt_packaged": {
            "system": system_prompt,
            "user": args.input
        },
        "response": result_text
    }
    if routing_info:
        run_log["routing_decision"] = routing_info
        
    log_path = os.path.join("artifacts", f"subagent_{args.agent}_run.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2)
        
    print(f"[SUBAGENT] Execution trace saved to: {log_path}")
    print("\n--- Subagent Output ---")
    print(result_text)
    print("-----------------------\n")

if __name__ == "__main__":
    main()
