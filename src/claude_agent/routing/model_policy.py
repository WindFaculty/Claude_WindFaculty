import os
import re
import json
import time
import logging

logger = logging.getLogger("claude_agent.routing.model_policy")

# Mandatory trigger keywords for Claude Sonnet escalation
ESCALATION_KEYWORDS = [
    "hard", "complex", "architecture", "security", "performance",
    "refactor large", "multi-file", "benchmark", "root cause",
    "production", "migration"
]

# Non-escalation keywords (bypass escalation)
BYPASS_KEYWORDS = [
    "typo", "documentation", "docstring", "comment", "readme",
    "spelling", "formatting", "question", "ask"
]

def estimate_tokens(text):
    """Simple robust character-based token estimator (approx 4 chars per token)."""
    if not text:
        return 0
    return len(text) // 4

def calculate_complexity_score(prompt_text, messages=None):
    """
    Computes a complexity score (0-10) based on prompt keyword matching,
    length of context, and message history count.
    """
    score = 0
    prompt_lower = prompt_text.lower()
    
    # 1. Keyword density
    for kw in ESCALATION_KEYWORDS:
        if kw in prompt_lower:
            score += 2
            
    # 2. String length indicator
    text_len = len(prompt_lower)
    if text_len > 15000:
        score += 3
    elif text_len > 5000:
        score += 2
    elif text_len > 2000:
        score += 1
        
    # 3. Message count complexity
    if messages and len(messages) > 4:
        score += 2
    elif messages and len(messages) > 2:
        score += 1
        
    # Cap between 0 and 10
    return min(10, max(0, score))

def evaluate_routing_policy(prompt_text, messages=None, agent_name=None, force_sonnet=False, force_haiku=False, no_escalation=False):
    """
    Evaluates the model policy configuration and returns a dictionary of routing decisions.
    """
    # 1. Load env variables with default routing parameters
    enable_escalation = os.getenv("CLAUDE_ROUTING_ENABLE_ESCALATION", "true").lower() == "true"
    max_input_tokens_haiku = int(os.getenv("CLAUDE_ROUTING_MAX_INPUT_TOKENS_HAIKU", "120000"))
    escalate_on_val_fail = os.getenv("CLAUDE_ROUTING_ESCALATE_ON_VALIDATION_FAIL", "true").lower() == "true"
    escalate_on_repair_loop = os.getenv("CLAUDE_ROUTING_ESCALATE_ON_REPAIR_LOOP", "true").lower() == "true"
    escalate_on_complexity_score = int(os.getenv("CLAUDE_ROUTING_ESCALATE_ON_COMPLEXITY_SCORE", "7"))
    
    selected_model = "haiku_4_5"
    escalated = False
    reasons = []
    
    # 2. Check for manual/CLI force flags
    if force_sonnet:
        selected_model = "sonnet_4_6"
        escalated = True
        reasons.append("forced_via_cli_flag")
        return _make_decision_dict(selected_model, escalated, reasons, 10)
        
    if force_haiku:
        selected_model = "haiku_4_5"
        escalated = False
        reasons.append("forced_haiku_via_cli")
        return _make_decision_dict(selected_model, escalated, reasons, 0)
        
    # 3. Evaluate non-escalation/bypass overrides first
    prompt_lower = prompt_text.lower()
    has_bypass_keyword = any(kw in prompt_lower for kw in BYPASS_KEYWORDS)
    
    # If escalation is disabled globally
    if not enable_escalation or no_escalation:
        selected_model = "haiku_4_5"
        escalated = False
        reasons.append("escalation_disabled_by_config")
        return _make_decision_dict(selected_model, escalated, reasons, calculate_complexity_score(prompt_text, messages))

    # 4. Check Context Token Size Limit
    estimated_tokens_count = estimate_tokens(prompt_text)
    if messages:
        for msg in messages:
            estimated_tokens_count += estimate_tokens(msg.get("content", ""))
            
    if estimated_tokens_count > max_input_tokens_haiku:
        selected_model = "sonnet_4_6"
        escalated = True
        reasons.append("haiku_token_limit_exceeded")
        
    # 5. Check Previous Run Validation Failures
    if escalate_on_val_fail:
        # Check diff_validation or test_validation failure
        prev_failed = False
        for val_file in ["diff_validation.json", "test_validation.json", "security_validation.json"]:
            path = os.path.join("artifacts", val_file)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("passed") is False:
                            prev_failed = True
                            reasons.append(f"previous_{val_file.split('_')[0]}_failed")
                except Exception:
                    pass
        if prev_failed:
            selected_model = "sonnet_4_6"
            escalated = True
            
    # 6. Check for active repair loops (retry loops >= 2)
    if escalate_on_repair_loop:
        # Look for repair plan or history indicating loop cycle >= 2
        path = os.path.join("artifacts", "repair_history.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    # Simple list of attempts or field matching retry index
                    attempts = len(history) if isinstance(history, list) else history.get("attempts", 0)
                    if attempts >= 2:
                        selected_model = "sonnet_4_6"
                        escalated = True
                        reasons.append("active_repair_loop_detected")
            except Exception:
                pass

    # 7. Check Agent Identity complexity
    if agent_name and agent_name in ["security-reviewer", "diff-reviewer", "test-diagnoser"]:
        # Subagents dealing with deep evaluation escalate easily
        selected_model = "sonnet_4_6"
        escalated = True
        reasons.append(f"specialist_agent_escalation_{agent_name}")

    # 8. Compute Complexity Score
    complexity = calculate_complexity_score(prompt_text, messages)
    if complexity >= escalate_on_complexity_score:
        selected_model = "sonnet_4_6"
        escalated = True
        reasons.append(f"complexity_score_exceeded_{complexity}")
        
    # 9. Direct Keyword matches in prompt
    matched_kws = [kw for kw in ESCALATION_KEYWORDS if kw in prompt_lower]
    if matched_kws:
        # If complexity was close or keywords are prominent, select Sonnet
        if len(matched_kws) >= 2:
            selected_model = "sonnet_4_6"
            escalated = True
            reasons.append(f"matched_escalation_keywords_{len(matched_kws)}")

    # 10. Check if user bypass explicitly forbids escalation (bypass wins unless token size overflows)
    if has_bypass_keyword and estimated_tokens_count <= max_input_tokens_haiku:
        selected_model = "haiku_4_5"
        escalated = False
        reasons = [r for r in reasons if "forced" in r]
        reasons.append("bypass_keywords_matched")

    # Clean duplicates in reasons
    reasons = list(set(reasons))
    if not reasons:
        reasons.append("default_haiku_policy")

    return _make_decision_dict(selected_model, escalated, reasons, complexity)

def _make_decision_dict(selected_model, escalated, reasons, complexity_score):
    """Helper to assemble a uniform decision dict and write audit log."""
    decision = {
        "provider": "aws_bedrock",
        "selected_model": selected_model,
        "selected_model_id_env": "AWS_BEDROCK_HAIKU_4_5_MODEL_ID" if selected_model == "haiku_4_5" else "AWS_BEDROCK_SONNET_4_6_MODEL_ID",
        "escalated": escalated,
        "escalation_target": "sonnet_4_6" if not escalated else "none",
        "reasons": reasons,
        "complexity_score": complexity_score,
        "budget_guard": "allow",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Save routing decision artifact
    os.makedirs("artifacts", exist_ok=True)
    decision_path = os.path.join("artifacts", "routing_decision.json")
    try:
        with open(decision_path, "w", encoding="utf-8") as f:
            json.dump(decision, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write routing_decision.json artifact: {str(e)}")
        
    return decision
