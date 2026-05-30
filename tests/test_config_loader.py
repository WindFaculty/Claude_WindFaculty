import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.claude_agent.config_loader import load_models_config

def test_config_loader_default_fallback():
    """Verify that configuration loader returns standard default fallbacks if file is absent."""
    with patch("os.path.exists", return_value=False):
        cfg = load_models_config()
        assert cfg["providers"]["aws_bedrock"]["enabled"] is True
        assert cfg["providers"]["aws_bedrock"]["region_env"] == "AWS_REGION"
        assert cfg["models"]["haiku_4_5"]["model_id_env"] == "AWS_BEDROCK_HAIKU_4_5_MODEL_ID"
        assert cfg["models"]["sonnet_4_6"]["max_retries"] == 1

def test_config_loader_yaml_parsing():
    """Verify that configuration loader correctly extracts key values from YAML strings."""
    mock_yaml = """
providers:
  aws_bedrock:
    enabled: true
    region_env: AWS_TEST_REGION
    profile_env: AWS_TEST_PROFILE
    default_model: test_haiku
    escalation_model: test_sonnet

models:
  haiku_4_5:
    provider: aws_bedrock
    model_id_env: AWS_TEST_HAIKU_MODEL_ID
    max_retries: 5

  sonnet_4_6:
    provider: aws_bedrock
    model_id_env: AWS_TEST_SONNET_MODEL_ID
    max_retries: 3
"""
    def mock_exists(path):
        return "models.yaml" in path
        
    def mock_open(path, mode="r", encoding=None):
        m = MagicMock()
        m.__enter__.return_value = m
        m.read.return_value = mock_yaml
        return m

    with patch("os.path.exists", side_effect=mock_exists), \
         patch("builtins.open", side_effect=mock_open):
        cfg = load_models_config()
        
        # Provider assertions
        provider_cfg = cfg["providers"]["aws_bedrock"]
        assert provider_cfg["enabled"] is True
        assert provider_cfg["region_env"] == "AWS_TEST_REGION"
        assert provider_cfg["profile_env"] == "AWS_TEST_PROFILE"
        assert provider_cfg["default_model"] == "test_haiku"
        assert provider_cfg["escalation_model"] == "test_sonnet"
        
        # Model assertions
        haiku_cfg = cfg["models"]["haiku_4_5"]
        assert haiku_cfg["model_id_env"] == "AWS_TEST_HAIKU_MODEL_ID"
        assert haiku_cfg["max_retries"] == 5
        
        sonnet_cfg = cfg["models"]["sonnet_4_6"]
        assert sonnet_cfg["model_id_env"] == "AWS_TEST_SONNET_MODEL_ID"
        assert sonnet_cfg["max_retries"] == 3
