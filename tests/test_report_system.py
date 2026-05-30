import sys
import os
import pytest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.reports.write_report import (
    get_git_diff_stats,
    extract_task_title,
    read_artifact_json
)

class SandboxTaskFile:
    def __init__(self, content):
        self.content = content
        self.task_path = "task.md"
        self.backup_path = "task.md.bak"
        self.backed_up = False

    def __enter__(self):
        # Backup if original exists
        if os.path.exists(self.task_path):
            if os.path.exists(self.backup_path):
                os.remove(self.backup_path)
            os.rename(self.task_path, self.backup_path)
            self.backed_up = True
            
        # Write mock data
        with open(self.task_path, "w", encoding="utf-8") as f:
            f.write(self.content)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.task_path):
            os.remove(self.task_path)
        # Restore backup
        if self.backed_up and os.path.exists(self.backup_path):
            os.rename(self.backup_path, self.task_path)

def test_report_templates_exist():
    """Verify that required templates are present."""
    task_template = os.path.join("reports", "templates", "task_report.md")
    bench_template = os.path.join("reports", "templates", "benchmark_report.md")
    
    assert os.path.exists(task_template) is True
    assert os.path.exists(bench_template) is True

def test_git_diff_stats_format():
    """Verify that get_git_diff_stats returns expected structure."""
    changed_files, additions, deletions, stat_msg = get_git_diff_stats()
    
    assert isinstance(changed_files, list)
    assert isinstance(additions, int)
    assert isinstance(deletions, int)
    assert isinstance(stat_msg, str)
    
    # If no changes in active workspace, assert counts are 0
    if not changed_files:
        assert additions == 0
        assert deletions == 0
        assert "No active" in stat_msg

def test_extract_task_title():
    """Test extract_task_title correctly parses markdown H1 headings."""
    mock_content = "# Mock Task H1 Title Heading\nSome content here..."
    
    with SandboxTaskFile(mock_content):
        title = extract_task_title()
        assert title == "Mock Task H1 Title Heading"

def test_read_artifact_json():
    """Test reading json logs safely from the artifacts folder."""
    mock_log = {"status": "TEST_OK", "exit_code": 0}
    os.makedirs("artifacts", exist_ok=True)
    temp_path = os.path.join("artifacts", "mock_log_test_only.json")
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_log, f)
            
        data = read_artifact_json("mock_log_test_only.json")
        assert data is not None
        assert data["status"] == "TEST_OK"
        assert data["exit_code"] == 0
        
        # Test missing log
        assert read_artifact_json("non_existent_log_12345.json") is None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
