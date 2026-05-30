import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.claude_agent.providers.aws_bedrock import AwsBedrockClaudeProvider

def test_resolve_model_id_defaults():
    """Test standard model alias resolutions."""
    provider = AwsBedrockClaudeProvider(region_name="us-west-2")
    
    # Check default model IDs
    assert provider._resolve_model_id("haiku_4_5") == "anthropic.claude-3-5-haiku-20241022-v1:0"
    assert provider._resolve_model_id("sonnet_4_6") == "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    # Custom IDs
    assert provider._resolve_model_id("anthropic.custom-model-id") == "anthropic.custom-model-id"
    assert provider._resolve_model_id("invalid-alias") is None

def test_resolve_model_id_env_overrides():
    """Test model alias resolutions utilizing custom env settings."""
    custom_haiku = "anthropic.custom-haiku-id"
    custom_sonnet = "anthropic.custom-sonnet-id"
    
    with patch.dict(os.environ, {
        "AWS_BEDROCK_HAIKU_4_5_MODEL_ID": custom_haiku,
        "AWS_BEDROCK_SONNET_4_6_MODEL_ID": custom_sonnet
    }):
        provider = AwsBedrockClaudeProvider()
        assert provider._resolve_model_id("haiku_4_5") == custom_haiku
        assert provider._resolve_model_id("sonnet_4_6") == custom_sonnet

def test_mask_model_id():
    """Test masking of accounts details in model IDs."""
    provider = AwsBedrockClaudeProvider()
    assert provider._mask_model_id("anthropic.claude-3-5-haiku-20241022-v1:0") == "anthropi...022-v1:0"
    assert provider._mask_model_id("short-id") == "short-id"
    assert provider._mask_model_id(None) == ""

@patch("boto3.Session")
def test_provider_completion_success(mock_session_class):
    """Test client completions using mocked boto3 bedrock client."""
    # 1. Setup mocks
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.client.return_value = mock_client
    
    # Mock return body read
    mock_body = MagicMock()
    mock_response = {
        "body": mock_body,
        "contentType": "application/json"
    }
    
    mock_response_payload = {
        "content": [{"type": "text", "text": "Successfully simulated Bedrock output!"}],
        "usage": {"input_tokens": 15, "output_tokens": 25},
        "stop_reason": "end_turn"
    }
    mock_body.read.return_value = json.dumps(mock_response_payload).encode("utf-8")
    mock_client.invoke_model.return_value = mock_response
    
    # 2. Query provider
    provider = AwsBedrockClaudeProvider(region_name="us-east-1", access_key="AKIA123", secret_key="SEC456")
    provider.client = mock_client # Ensure client override
    
    messages = [{"role": "user", "content": "Hello!"}]
    content, err = provider.complete(messages, system_prompt="Sys prompt test", model_alias="haiku_4_5")
    
    # 3. Assertions
    assert err is None
    assert content == "Successfully simulated Bedrock output!"
    
    # Verify mock call parameters
    mock_client.invoke_model.assert_called_once()
    called_args, called_kwargs = mock_client.invoke_model.call_args
    assert called_kwargs["modelId"] == "anthropic.claude-3-5-haiku-20241022-v1:0"
    
    payload = json.loads(called_kwargs["body"].decode("utf-8"))
    assert payload["system"] == "Sys prompt test"
    assert payload["messages"] == messages
    assert payload["anthropic_version"] == "bedrock-2023-05-31"

@patch("boto3.Session")
def test_provider_completion_error_handling(mock_session_class):
    """Test provider exception and error response processes."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.client.return_value = mock_client
    
    mock_client.invoke_model.side_effect = Exception("AWS Access Denied Sim error")
    
    provider = AwsBedrockClaudeProvider()
    provider.client = mock_client
    
    content, err = provider.complete([{"role": "user", "content": "test"}])
    assert content is None
    assert "AWS Access Denied Sim error" in err
