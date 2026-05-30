import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.bootstrap.verify_environment import (
    check_python_version,
    check_required_directories,
    check_configs
)

def test_python_version_verification():
    passed, msg = check_python_version()
    assert passed is True
    assert "Python" in msg

def test_directories_existence():
    passed, msg = check_required_directories()
    assert passed is True
    assert "All required directories exist" in msg

def test_configs_validity():
    passed, msg = check_configs()
    assert passed is True
    assert "parsed successfully" in msg
