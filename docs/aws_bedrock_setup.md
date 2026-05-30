# AWS Bedrock Claude Integration & Setup Guide

This guide describes how to configure AWS Bedrock as the primary Claude model provider for the `Claude_WindFaculty` environment.

---

## 1. Enable Claude Models in AWS Console

Before calling models via API, you must request and enable model access in your AWS Bedrock account:

1. Open the **AWS Bedrock Console**.
2. Make sure you are in a region that supports Claude (e.g., `us-east-1` N. Virginia or `us-west-2` Oregon).
3. In the left navigation pane, scroll to the bottom and select **Model access**.
4. Click **Manage model access** in the top right.
5. Tick the checkboxes next to:
   - **Claude 3.5 Haiku** (or the target default model)
   - **Claude 3.5 Sonnet / Claude 3.7 Sonnet** (or the target escalation model)
6. Click **Save changes** and wait for the access status to display as **Access granted**.

---

## 2. Minimal Recommended IAM Permissions

To run interactions safely and prevent excess exposure, assign the following minimal IAM policy to the target AWS Profile or IAM User executing the agent:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ClaudeModelInvocation",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
        "arn:aws:bedrock:*::foundation-model/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Sid": "BedrockDiagnostics",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

> [!WARNING]
> Do not use wildcards like `bedrock:*` or administrative roles for development or production environments. Keep resource bounds restricted to Anthropic Claude models.

---

## 3. Environment Variables Configuration

Add the following configurations to your local `.env` file (which is git-ignored):

```env
# AWS Connection Parameters
AWS_REGION=us-east-1
AWS_PROFILE=my-developer-profile

# Static Credentials (Optional, preferred over named profile if set)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=

# Model Routing Parameters
CLAUDE_PROVIDER=aws_bedrock
CLAUDE_DEFAULT_MODEL=haiku_4_5
CLAUDE_ESCALATION_MODEL=sonnet_4_6

# Target Model IDs (Configurable so you can easily point to specific endpoints)
AWS_BEDROCK_HAIKU_4_5_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
AWS_BEDROCK_SONNET_4_6_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0

# Router Policy Thresholds
CLAUDE_ROUTING_ENABLE_ESCALATION=true
CLAUDE_ROUTING_MAX_HAIKU_RETRIES=2
CLAUDE_ROUTING_MAX_SONNET_RETRIES=1
CLAUDE_ROUTING_MAX_INPUT_TOKENS_HAIKU=120000
CLAUDE_ROUTING_ESCALATE_ON_VALIDATION_FAIL=true
CLAUDE_ROUTING_ESCALATE_ON_CONTEXT_OVERFLOW=true
CLAUDE_ROUTING_ESCALATE_ON_REPAIR_LOOP=true
CLAUDE_ROUTING_ESCALATE_ON_COMPLEXITY_SCORE=7
```

---

## 4. Operational Diagnostics and Verification

Verify that your AWS environment, authentication, and models are fully operational:

### 1. Check Credentials and Connection Configuration
Inspect environment variables, import boto3 package, test AWS authentication, and list available foundation models:
```bash
python scripts/aws_bedrock_check.py
```

### 2. Execute a Safe Smoke Invocations Test
Test connection latency and retrieve model capabilities with minimal tokens (queries with: "Return exactly: ok"):
```bash
# Test default Haiku 4.5
python scripts/aws_bedrock_smoke.py --model haiku

# Test escalation Sonnet 4.6
python scripts/aws_bedrock_smoke.py --model sonnet

# Test both models sequentially
python scripts/aws_bedrock_smoke.py --model both
```

The smoke test will output a detailed latency and metrics report saved under `reports/aws_bedrock_smoke_<timestamp>.json`.
