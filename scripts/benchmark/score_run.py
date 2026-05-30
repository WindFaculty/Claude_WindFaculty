#!/usr/bin/env python
"""
Benchmark Scoring Engine
Calculates standard metrics (Accuracy, Speed, Token/Resource Efficiency) based on weights defined in configs/benchmark.yaml.
"""
import os
import sys
import re
import json
import argparse

def load_scoring_config():
    """Load scoring weights from configs/benchmark.yaml using a zero-dependency regex parser."""
    config_path = os.path.join("configs", "benchmark.yaml")
    weights = {
        "accuracy_weight": 0.6,
        "speed_weight": 0.2,
        "token_efficiency_weight": 0.2
    }
    
    if not os.path.exists(config_path):
        return weights
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        acc_match = re.search(r"accuracy_weight:\s*([\d\.]+)", content)
        if acc_match:
            weights["accuracy_weight"] = float(acc_match.group(1))
            
        speed_match = re.search(r"speed_weight:\s*([\d\.]+)", content)
        if speed_match:
            weights["speed_weight"] = float(speed_match.group(1))
            
        tok_match = re.search(r"token_efficiency_weight:\s*([\d\.]+)", content)
        if tok_match:
            weights["token_efficiency_weight"] = float(tok_match.group(1))
            
        return weights
    except Exception:
        return weights

def calculate_token_efficiency():
    """Evaluate context efficiency using limits from configs/context.yaml."""
    context_json = os.path.join("artifacts", "selected_context.json")
    if not os.path.exists(context_json):
        return 100.0 # Baseline if task didn't require context packing
        
    try:
        with open(context_json, "r", encoding="utf-8") as f:
            selected_files = json.load(f)
            
        num_files = len(selected_files)
        
        # Load warning and max limits from configs/context.yaml
        warning_limit = 12
        max_limit = 20
        
        context_yaml = os.path.join("configs", "context.yaml")
        if os.path.exists(context_yaml):
            with open(context_yaml, "r", encoding="utf-8") as f:
                content = f.read()
            warn_match = re.search(r"warning_files_selected:\s*(\d+)", content)
            if warn_match:
                warning_limit = int(warn_match.group(1))
            max_match = re.search(r"max_files_selected:\s*(\d+)", content)
            if max_match:
                max_limit = int(max_match.group(1))
                
        if num_files <= warning_limit:
            return 100.0
        elif num_files <= max_limit:
            return 80.0
        else:
            return 50.0
    except Exception:
        return 100.0

def score_task(task_result, weights=None):
    """
    Computes a weighted performance score for a task.
    """
    if weights is None:
        weights = load_scoring_config()
        
    # 1. Accuracy Score (weighted command success & artifact checks)
    cmd_success = task_result.get("exit_code_success", False)
    cmd_score = 100.0 if cmd_success else 0.0
    
    artifacts = task_result.get("artifacts_checked", [])
    if artifacts:
        found_count = sum(1 for a in artifacts if a.get("exists", False))
        artifact_score = (found_count / len(artifacts)) * 100.0
        # Accuracy is 50% command success + 50% artifact success
        accuracy_score = (cmd_score * 0.5) + (artifact_score * 0.5)
    else:
        accuracy_score = cmd_score
        
    # 2. Speed Score (decay based on elapsed time vs timeout)
    elapsed = task_result.get("elapsed_seconds", 0.0)
    timeout = task_result.get("timeout_seconds", 30.0)
    if elapsed >= timeout or task_result.get("timeout_triggered", False):
        speed_score = 0.0
    else:
        speed_score = (1.0 - (elapsed / timeout)) * 100.0
        
    # 3. Token/Resource Efficiency Score
    # Only calculate token score if the task is context selection or code edit,
    # otherwise default to 100.0
    task_id = task_result.get("task_id", "")
    if task_id in ("context_selection", "code_edit"):
        token_score = calculate_token_efficiency()
    else:
        token_score = 100.0
        
    # Final weighted score
    final_score = (
        accuracy_score * weights["accuracy_weight"] +
        speed_score * weights["speed_weight"] +
        token_score * weights["token_efficiency_weight"]
    )
    
    scored_result = {
        "task_id": task_id,
        "name": task_result.get("name", ""),
        "success": task_result.get("success", False),
        "scores": {
            "accuracy": round(accuracy_score, 1),
            "speed": round(speed_score, 1),
            "token_efficiency": round(token_score, 1),
            "final": round(final_score, 1)
        },
        "weights": weights,
        "elapsed_seconds": round(elapsed, 2)
    }
    
    return scored_result

def main():
    parser = argparse.ArgumentParser(description="Score a task run execution result")
    parser.add_argument("--result_json", type=str, required=True, help="Path to JSON file containing the task execution result")
    args = parser.parse_args()
    
    if not os.path.exists(args.result_json):
        print(f"[ERROR] Result JSON file not found: {args.result_json}")
        sys.exit(1)
        
    try:
        with open(args.result_json, "r", encoding="utf-8") as f:
            result_data = json.load(f)
            
        weights = load_scoring_config()
        scored = score_task(result_data, weights)
        print(json.dumps(scored, indent=2))
    except Exception as e:
        print(f"[ERROR] Failed scoring execution result: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
