import sys
import os
import pytest
import json
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We can run these script tests by importing main or calling subprocess on mocks.
# Let's mock boto3 to verify aws_bedrock_check.py
@patch("boto3.Session")
def test_aws_bedrock_check_script(mock_session_class):
    """Test verification steps in aws_bedrock_check.py."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.client.return_value = mock_client
    
    mock_client.list_foundation_models.return_value = {
        "modelSummaries": [
            {"modelId": "anthropic.claude-3-5-haiku-20241022-v1:0", "modelName": "Claude 3.5 Haiku"},
            {"modelId": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", "modelName": "Claude 3.7 Sonnet"}
        ]
    }
    
    from scripts.aws_bedrock_check import main as check_main
    
    # Capture stdout
    with patch("sys.stdout.write") as mock_write:
        try:
            check_main()
        except SystemExit as ex:
            assert ex.code == 0
            
    mock_client.list_foundation_models.assert_called_once_with(byProvider="Anthropic")

@patch("src.claude_agent.providers.aws_bedrock.AwsBedrockClaudeProvider.complete")
def test_aws_bedrock_smoke_script(mock_complete):
    """Test invoke process and reporting in aws_bedrock_smoke.py."""
    mock_complete.return_value = ("ok - test simulation pass", None)
    
    # 1. Prepare CLI parameters
    test_args = ["scripts/aws_bedrock_smoke.py", "--model", "haiku"]
    
    from scripts.aws_bedrock_smoke import main as smoke_main
    
    # Clear any previous smoke files to ensure clean assertion
    for f in os.listdir("reports"):
        if f.startswith("aws_bedrock_smoke_") and f.endswith(".json"):
            try:
                os.remove(os.path.join("reports", f))
            except Exception:
                pass
                
    with patch("sys.argv", test_args):
        try:
            smoke_main()
        except SystemExit as ex:
            assert ex.code == 0
            
    # Verify report is written
    report_found = False
    for f in os.listdir("reports"):
        if f.startswith("aws_bedrock_smoke_") and f.endswith(".json"):
            report_found = True
            filepath = os.path.join("reports", f)
            with open(filepath, "r", encoding="utf-8") as rf:
                data = json.load(rf)
                assert data["overall_success"] is True
                assert "haiku_4_5" in data["results"]
                assert data["results"]["haiku_4_5"]["passed"] is True
            # Clean up
            os.remove(filepath)
            break
            
    assert report_found is True
