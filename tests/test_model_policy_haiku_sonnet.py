import sys
import os
import pytest
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.claude_agent.routing.model_policy import (
    calculate_complexity_score,
    evaluate_routing_policy,
    estimate_tokens
)

def test_token_estimator():
    """Verify estimate_tokens calculation accuracy."""
    assert estimate_tokens("hello") == 1
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("") == 0

def test_complexity_scoring():
    """Verify score levels based on keywords and lengths."""
    # Low complexity
    score_low = calculate_complexity_score("Asking a small query regarding a spelling error in a comment.")
    assert score_low < 3
    
    # Keyword matches
    score_kw = calculate_complexity_score("Please perform a complex performance refactor of our database migration architecture.")
    assert score_kw >= 4
    
    # Large context
    score_large = calculate_complexity_score("a" * 25000)
    assert score_large >= 3

def test_default_haiku_routing():
    """Check standard query routes to Haiku 4.5 by default."""
    decision = evaluate_routing_policy("How do I add comments in python?")
    assert decision["selected_model"] == "haiku_4_5"
    assert decision["escalated"] is False
    assert "default_haiku_policy" in decision["reasons"] or "bypass_keywords_matched" in decision["reasons"]

def test_keyword_escalation():
    """Check prominent keyword triggers escalate to Sonnet 4.6."""
    decision = evaluate_routing_policy("Implement a production migration architecture for root cause performance checks.")
    assert decision["selected_model"] == "sonnet_4_6"
    assert decision["escalated"] is True
    assert any("keywords" in r or "complexity" in r for r in decision["reasons"])

def test_token_overflow_escalation():
    """Verify that estimated token sizes exceeding limit trigger Sonnet."""
    # Trigger token overflow by mocking a large input
    large_prompt = "x" * 600000 # ~150k estimated tokens, default cap 120k
    
    decision = evaluate_routing_policy(large_prompt)
    assert decision["selected_model"] == "sonnet_4_6"
    assert decision["escalated"] is True
    assert "haiku_token_limit_exceeded" in decision["reasons"]

def test_force_cli_overrides():
    """Test manual overrides from CLI flags."""
    # Force Sonnet
    decision = evaluate_routing_policy("easy query", force_sonnet=True)
    assert decision["selected_model"] == "sonnet_4_6"
    assert decision["escalated"] is True
    assert "forced_via_cli_flag" in decision["reasons"]
    
    # Force Haiku (even with complex prompt)
    decision2 = evaluate_routing_policy("production migration architecture performance", force_haiku=True)
    assert decision2["selected_model"] == "haiku_4_5"
    assert decision2["escalated"] is False

def test_non_escalation_bypass():
    """Verify bypass keywords override standard escalation triggers."""
    # Although "migration" is an escalation keyword, "typo" and "documentation" should bypass it
    decision = evaluate_routing_policy("fix a spelling typo in migration documentation")
    assert decision["selected_model"] == "haiku_4_5"
    assert decision["escalated"] is False
    assert "bypass_keywords_matched" in decision["reasons"]

def test_validation_failure_escalation():
    """Verify previous validation failures trigger escalation on subsequent run evaluations."""
    mock_failed_validation = {"passed": False, "verdict": "WRONG_FILE_EDIT"}
    
    # Mock existence of failing validation file
    def mock_exists(path):
        return "diff_validation.json" in path
        
    def mock_open(path, mode="r", encoding=None):
        m = MagicMock()
        m.__enter__.return_value = m
        m.read.return_value = json.dumps(mock_failed_validation)
        return m

    with patch("os.path.exists", side_effect=mock_exists), \
         patch("builtins.open", side_effect=mock_open):
        decision = evaluate_routing_policy("normal query")
        assert decision["selected_model"] == "sonnet_4_6"
        assert decision["escalated"] is True
        assert "previous_diff_failed" in decision["reasons"]
