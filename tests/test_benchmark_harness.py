import sys
import os
import pytest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.benchmark.run_suite import parse_suite_yaml

def test_yaml_suites_parse():
    """Verify that all newly created yaml suites parse cleanly."""
    for suite in ["bugfix", "refactor", "repo_intake"]:
        path = os.path.join("benchmarks", "suites", f"{suite}.yaml")
        assert os.path.exists(path) is True
        
        data = parse_suite_yaml(path)
        assert data["name"] == suite
        assert len(data["description"]) > 10
        assert len(data["tasks"]) >= 2
        
        for task in data["tasks"]:
            assert "task_id" in task
            assert "name" in task
            assert "command" in task
            assert isinstance(task.get("timeout", 30), int)
            assert isinstance(task.get("expected_artifacts", []), list)

def test_expected_metrics_loads():
    """Verify that expected_metrics.json loads and contains correct structure."""
    path = os.path.join("benchmarks", "expected", "expected_metrics.json")
    assert os.path.exists(path) is True
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "baselines" in data
    baselines = data["baselines"]
    
    for suite in ["smoke", "bugfix", "refactor", "repo_intake"]:
        assert suite in baselines
        suite_base = baselines[suite]
        assert "expected_average_score" in suite_base
        assert "expected_duration_max_sec" in suite_base
        assert "expected_exit_code" in suite_base

def test_task_markdowns_complete():
    """Verify that the diagnostic markdown tasks are complete and well-formed."""
    for idx in range(1, 4):
        path = os.path.join("benchmarks", "tasks", f"task_00{idx}.md")
        assert os.path.exists(path) is True
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        assert content.startswith("#")
        assert "## Description" in content
        assert "## Requirements" in content
        assert "## Targeted Files" in content
