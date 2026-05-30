import os
import re

def load_models_config():
    """
    Zero-dependency YAML parser for configs/models.yaml.
    Returns parsed dictionaries for providers and models.
    """
    config_path = os.path.join("configs", "models.yaml")
    
    # Default fallback values matching current configurations
    config = {
        "providers": {
            "aws_bedrock": {
                "enabled": True,
                "region_env": "AWS_REGION",
                "profile_env": "AWS_PROFILE",
                "default_model": "haiku_4_5",
                "escalation_model": "sonnet_4_6"
            }
        },
        "models": {
            "haiku_4_5": {
                "provider": "aws_bedrock",
                "model_id_env": "AWS_BEDROCK_HAIKU_4_5_MODEL_ID",
                "role": "default",
                "max_retries": 2
            },
            "sonnet_4_6": {
                "provider": "aws_bedrock",
                "model_id_env": "AWS_BEDROCK_SONNET_4_6_MODEL_ID",
                "role": "escalation",
                "max_retries": 1
            }
        }
    }
    
    if not os.path.exists(config_path):
        return config
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Helper to extract value using regex
        def get_yaml_val(parent, child, default_val, is_bool=False, is_int=False):
            # Matches key: under parent block
            pattern = rf"{parent}:\s*\n(?:.*\n)*?\s+{child}:\s*([^\n]+)"
            match = re.search(pattern, content)
            if not match:
                # Fallback to single match if indentation is standard
                pattern_fallback = rf"\s+{child}:\s*([^\n]+)"
                match = re.search(pattern_fallback, content)
                if not match:
                    return default_val
            
            val = match.group(1).strip().strip("'\"")
            if is_bool:
                return val.lower() == "true"
            if is_int:
                try:
                    return int(val)
                except ValueError:
                    return default_val
            return val

        # 1. Parse Providers
        config["providers"]["aws_bedrock"]["enabled"] = get_yaml_val("aws_bedrock", "enabled", True, is_bool=True)
        config["providers"]["aws_bedrock"]["region_env"] = get_yaml_val("aws_bedrock", "region_env", "AWS_REGION")
        config["providers"]["aws_bedrock"]["profile_env"] = get_yaml_val("aws_bedrock", "profile_env", "AWS_PROFILE")
        config["providers"]["aws_bedrock"]["default_model"] = get_yaml_val("aws_bedrock", "default_model", "haiku_4_5")
        config["providers"]["aws_bedrock"]["escalation_model"] = get_yaml_val("aws_bedrock", "escalation_model", "sonnet_4_6")
        
        # 2. Parse Models
        config["models"]["haiku_4_5"]["model_id_env"] = get_yaml_val("haiku_4_5", "model_id_env", "AWS_BEDROCK_HAIKU_4_5_MODEL_ID")
        config["models"]["haiku_4_5"]["max_retries"] = get_yaml_val("haiku_4_5", "max_retries", 2, is_int=True)
        
        config["models"]["sonnet_4_6"]["model_id_env"] = get_yaml_val("sonnet_4_6", "model_id_env", "AWS_BEDROCK_SONNET_4_6_MODEL_ID")
        config["models"]["sonnet_4_6"]["max_retries"] = get_yaml_val("sonnet_4_6", "max_retries", 1, is_int=True)
        
        return config
    except Exception:
        return config
