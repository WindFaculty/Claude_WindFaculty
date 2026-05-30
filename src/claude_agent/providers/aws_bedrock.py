import os
import sys
import json
import time
import logging

# Set up clean logging
logger = logging.getLogger("claude_agent.providers.aws_bedrock")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class AwsBedrockClaudeProvider:
    def __init__(self, region_name=None, profile_name=None, access_key=None, secret_key=None, session_token=None):
        """
        Initialize the AWS Bedrock client.
        Extracts credentials from params or standard env variable mappings.
        """
        # 1. Resolve configuration parameters
        self.region = region_name or os.getenv("AWS_REGION") or "us-east-1"
        self.profile = profile_name or os.getenv("AWS_PROFILE")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.session_token = session_token or os.getenv("AWS_SESSION_TOKEN")
        
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize the boto3 bedrock-runtime client."""
        try:
            import boto3
        except ImportError:
            # We don't fail immediately to allow dry runs and offline testing mocks
            logger.warning("boto3 is not installed. AWS Bedrock provider will only function under mock conditions.")
            return

        try:
            # 1. Setup Session parameters
            session_kwargs = {}
            if self.profile:
                session_kwargs["profile_name"] = self.profile
            if self.region:
                session_kwargs["region_name"] = self.region
            if self.access_key and self.secret_key:
                session_kwargs["aws_access_key_id"] = self.access_key
                session_kwargs["aws_secret_access_key"] = self.secret_key
                if self.session_token:
                    session_kwargs["aws_session_token"] = self.session_token

            # 2. Establish Session and Client
            session = boto3.Session(**session_kwargs)
            self.client = session.client("bedrock-runtime", region_name=self.region)
            logger.info(f"Successfully initialized AWS Bedrock Runtime client in region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock Client: {str(e)}")
            self.client = None

    def complete(self, messages, system_prompt=None, model_alias="haiku_4_5", max_tokens=2048, temperature=0.7, **kwargs):
        """
        Execute completion against the AWS Bedrock Claude model.
        Returns a tuple of (content, error_message).
        """
        # 1. Resolve model ID from environment or default alias
        model_id = self._resolve_model_id(model_alias)
        if not model_id:
            return None, f"Model ID resolution failed for model alias: {model_alias}. Verify env configuration."

        # Masked model ID for safe logging
        masked_model_id = self._mask_model_id(model_id)
        logger.info(f"Sending completion request. Model: {model_alias} (ID: {masked_model_id})")

        # 2. Check if client is initialized
        if not self.client:
            # Try to reinitialize client
            self._init_client()
            if not self.client:
                return None, "AWS Bedrock client is not initialized or credentials are missing/invalid."

        # 3. Construct Anthropic Messages format payload
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }
        if system_prompt:
            payload["system"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature

        # Incorporate additional parameters if provided
        for k, v in kwargs.items():
            if k not in payload:
                payload[k] = v

        # 4. Invoke the model and record metrics
        start_time = time.time()
        try:
            body_bytes = json.dumps(payload).encode("utf-8")
            response = self.client.invoke_model(
                modelId=model_id,
                body=body_bytes,
                contentType="application/json",
                accept="application/json"
            )
            latency = time.time() - start_time
            
            # Read and parse response
            response_body = response.get("body").read().decode("utf-8")
            response_json = json.loads(response_body)
            
            # Extract content text and usage statistics
            content_list = response_json.get("content", [])
            text_content = ""
            for item in content_list:
                if item.get("type") == "text":
                    text_content += item.get("text", "")
            
            usage = response_json.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            stop_reason = response_json.get("stop_reason", "unknown")
            
            # Save invocation metadata to a runtime log file
            self._log_metadata(model_alias, model_id, latency, input_tokens, output_tokens, stop_reason)
            
            return text_content, None

        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)
            logger.error(f"AWS Bedrock invoke_model failed: {error_msg}")
            
            # Write fail log
            self._log_metadata(model_alias, model_id, latency, 0, 0, "error", error_message=error_msg)
            return None, f"AWS Bedrock invoke error: {error_msg}"

    def _resolve_model_id(self, model_alias):
        """Resolves standard alias into an AWS Bedrock model ID via env settings or fallbacks."""
        if model_alias == "haiku_4_5":
            env_val = os.getenv("AWS_BEDROCK_HAIKU_4_5_MODEL_ID")
            return env_val or "anthropic.claude-3-5-haiku-20241022-v1:0"
        elif model_alias == "sonnet_4_6":
            env_val = os.getenv("AWS_BEDROCK_SONNET_4_6_MODEL_ID")
            return env_val or "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        else:
            # Directly use model_alias if it's already a full model id format
            if "." in model_alias or ":" in model_alias:
                return model_alias
            return None

    def _mask_model_id(self, model_id):
        """Safely masks model ID to protect any potential account-specific ARN suffixes in logs."""
        if not model_id:
            return ""
        if len(model_id) <= 15:
            return model_id
        return f"{model_id[:8]}...{model_id[-8:]}"

    def _log_metadata(self, alias, model_id, latency, input_tokens, output_tokens, stop_reason, error_message=None):
        """Saves operational metadata to a secure local audit artifact file."""
        os.makedirs("artifacts", exist_ok=True)
        log_filepath = os.path.join("artifacts", "aws_bedrock_invocations.jsonl")
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": "aws_bedrock",
            "model_alias": alias,
            "model_id_masked": self._mask_model_id(model_id),
            "latency_seconds": round(latency, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "stop_reason": stop_reason,
            "success": error_message is None
        }
        if error_message:
            log_entry["error"] = error_message
            
        try:
            with open(log_filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            # Fallback to standard console logger if write fails
            logger.warning(f"Could not write invocation metadata log: {str(e)}")
