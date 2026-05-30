import sys
import os
import pytest
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.benchmark.run_task import run_task
from scripts.benchmark.score_run import score_task, calculate_token_efficiency
from scripts.benchmark.run_suite import parse_suite_yaml

def test_run_task_success():
    """Test successful task execution."""
    res = run_task(
        task_id="test_success",
        name="Test Success Task",
        command='python -c "print(\'Hello World\')"',
        timeout=5,
        expected_exit_code=0
    )
    
    assert res["task_id"] == "test_success"
    assert res["exit_code"] == 0
    assert res["success"] is True
    assert "Hello World" in res["stdout_snippet"]
    assert res["elapsed_seconds"] > 0
    assert res["timeout_triggered"] is False

def test_run_task_fail_exit_code():
    """Test task execution returning incorrect exit code."""
    res = run_task(
        task_id="test_fail",
        name="Test Fail Task",
        command='python -c "import sys; sys.exit(42)"',
        timeout=5,
        expected_exit_code=0
    )
    
    assert res["exit_code"] == 42
    assert res["success"] is False
    assert res["exit_code_success"] is False

def test_run_task_artifact_checks():
    """Test expected artifacts checks."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name
        
    try:
        # Check artifact exists
        res = run_task(
            task_id="test_art",
            name="Test Artifact Task",
            command='python -c "pass"',
            timeout=5,
            expected_exit_code=0,
            expected_artifacts=[tmp_name]
        )
        assert res["artifacts_success"] is True
        assert res["success"] is True
        
        # Check artifact missing
        res_missing = run_task(
            task_id="test_art_missing",
            name="Test Artifact Missing Task",
            command='python -c "pass"',
            timeout=5,
            expected_exit_code=0,
            expected_artifacts=["path/does/not/exist/at/all/12345.json"]
        )
        assert res_missing["artifacts_success"] is False
        assert res_missing["success"] is False
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def test_scoring_calculations():
    """Test scoring math including weights, accuracy, speed."""
    weights = {
        "accuracy_weight": 0.6,
        "speed_weight": 0.2,
        "token_efficiency_weight": 0.2
    }
    
    # 1. 100% Accuracy and Speed
    task_res_perfect = {
        "task_id": "dummy",
        "exit_code_success": True,
        "success": True,
        "elapsed_seconds": 0.0,
        "timeout_seconds": 10.0,
        "artifacts_checked": []
    }
    score_res = score_task(task_res_perfect, weights)
    assert score_res["scores"]["accuracy"] == 100.0
    assert score_res["scores"]["speed"] == 100.0
    # defaults token efficiency to 100.0 for non-context tasks
    assert score_res["scores"]["final"] == 100.0
    
    # 2. Part Accuracy, part Speed
    task_res_partial = {
        "task_id": "dummy",
        "exit_code_success": True,
        "success": False,
        "elapsed_seconds": 5.0, # 50% speed score
        "timeout_seconds": 10.0,
        "artifacts_checked": [
            {"file": "a", "exists": True},
            {"file": "b", "exists": False} # 50% artifact success -> 75% accuracy total
        ]
    }
    score_res_partial = score_task(task_res_partial, weights)
    assert score_res_partial["scores"]["accuracy"] == 75.0 # 50% * 100 + 50% * 50
    assert score_res_partial["scores"]["speed"] == 50.0
    assert score_res_partial["scores"]["final"] == round(75.0*0.6 + 50.0*0.2 + 100.0*0.2, 1)

def test_yaml_parser():
    """Test YAML parser in suite runner using temp file."""
    yaml_content = """# Comment line
name: test_suite
description: Test suite description
tasks:
  - task_id: first_task
    name: "First Task Name"
    command: "python scripts/first.py"
    expected_exit_code: 0
    timeout: 10
    expected_artifacts:
      - "artifacts/first.json"
      - "reports/first.md"
      
  - task_id: second_task
    name: "Second Task Name"
    command: "python scripts/second.py"
    expected_exit_code: 1
    timeout: 5
"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml", encoding="utf-8") as tmp:
        tmp.write(yaml_content)
        tmp_name = tmp.name
        
    try:
        data = parse_suite_yaml(tmp_name)
        assert data["name"] == "test_suite"
        assert data["description"] == "Test suite description"
        assert len(data["tasks"]) == 2
        
        task1 = data["tasks"][0]
        assert task1["task_id"] == "first_task"
        assert task1["name"] == "First Task Name"
        assert task1["command"] == "python scripts/first.py"
        assert task1["expected_exit_code"] == 0
        assert task1["timeout"] == 10
        assert len(task1["expected_artifacts"]) == 2
        assert "artifacts/first.json" in task1["expected_artifacts"]
        
        task2 = data["tasks"][1]
        assert task2["task_id"] == "second_task"
        assert task2["expected_exit_code"] == 1
        assert task2["timeout"] == 5
        assert len(task2["expected_artifacts"]) == 0
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
