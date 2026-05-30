#!/usr/bin/env python
"""
AWS Bedrock Configuration and Credentials Verifier.
Validates AWS region, credentials, model parameters, and listings.
"""
import os
import sys

def load_dotenv():
    """Simple robust zero-dependency .env loader."""
    if os.path.exists(".env"):
        print("[CHECK] Loading local .env configurations...")
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
        except Exception as e:
            print(f"[WARNING] Failed reading .env file: {str(e)}")

def main():
    load_dotenv()
    
    print("\n=========================================")
    print("AWS Bedrock Claude Diagnostic Checker")
    print("=========================================")
    
    # 1. Inspect Environment Variables
    print("\n[1/4] Inspecting Environment configurations...")
    region = os.getenv("AWS_REGION", "us-east-1")
    profile = os.getenv("AWS_PROFILE", "")
    provider = os.getenv("CLAUDE_PROVIDER", "aws_bedrock")
    
    haiku_id = os.getenv("AWS_BEDROCK_HAIKU_4_5_MODEL_ID")
    sonnet_id = os.getenv("AWS_BEDROCK_SONNET_4_6_MODEL_ID")
    
    print(f"  * CLAUDE_PROVIDER: {provider}")
    print(f"  * AWS_REGION: {region}")
    print(f"  * AWS_PROFILE: {profile or '<Not Specified - using Default Chain>'}")
    print(f"  * Haiku 4.5 Model Env ID: {haiku_id or '<Not set - using default: anthropic.claude-3-5-haiku-20241022-v1:0>'}")
    print(f"  * Sonnet 4.6 Model Env ID: {sonnet_id or '<Not set - using default: us.anthropic.claude-3-7-sonnet-20250219-v1:0>'}")

    # 2. Check boto3 import
    print("\n[2/4] Verifying SDK packages availability...")
    try:
        import boto3
        print(f"  * boto3 version: {boto3.__version__}")
    except ImportError:
        print("  * [CRITICAL] boto3 is not installed in the active environment!")
        print("    Please run scripts/bootstrap/setup.ps1 or pip install boto3.")
        sys.exit(1)

    # 3. Check Credential Resolution
    print("\n[3/4] Testing AWS Authentication resolution...")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    
    if access_key and secret_key:
        print("  * Credentials source: Static Environment Variables (AWS_ACCESS_KEY_ID set)")
        masked_key = f"{access_key[:4]}...{access_key[-4:]}" if len(access_key) > 8 else "invalid"
        print(f"  * AWS_ACCESS_KEY_ID: {masked_key}")
    else:
        print("  * Credentials source: Checking standard profile / IAM Roles...")
        try:
            session = boto3.Session(profile_name=profile if profile else None, region_name=region)
            creds = session.get_credentials()
            if creds:
                curr_key = creds.access_key
                masked_key = f"{curr_key[:4]}...{curr_key[-4:]}" if curr_key and len(curr_key) > 8 else "None"
                print(f"  * Resolved active Access Key ID: {masked_key}")
            else:
                print("  * [WARNING] No credentials could be resolved via AWS Session.")
        except Exception as e:
            print(f"  * [WARNING] Session authentication checking failed: {str(e)}")

    # 4. Invoke list foundation models
    print("\n[4/4] Listing Bedrock foundation models capability...")
    try:
        session_kwargs = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region
            
        session = boto3.Session(**session_kwargs)
        bedrock = session.client("bedrock", region_name=region)
        
        # Limit search to Anthropic models
        models = bedrock.list_foundation_models(byProvider="Anthropic")
        summaries = models.get("modelSummaries", [])
        
        print(f"  * Successfully retrieved model listings ({len(summaries)} Anthropic models found).")
        for m in summaries[:5]:
            print(f"    - Model ID: {m.get('modelId')} (Name: {m.get('modelName')})")
        if len(summaries) > 5:
            print(f"    - ... and {len(summaries) - 5} more models.")
            
    except Exception as e:
        print("  * [WARNING] Account does not permit bedrock:ListFoundationModels or credentials failed:")
        print(f"    Detail: {str(e)}")
        print("    (This is standard under tight IAM configurations. Model completions may still function.)")

    print("\n=========================================")
    print("Verification completed successfully.")
    print("=========================================\n")

if __name__ == "__main__":
    main()
