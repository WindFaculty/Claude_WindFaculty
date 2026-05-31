#!/usr/bin/env python
"""CLI wrapper for the Claude hook reliability validator."""
import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.validate.validate_claude_hooks import main


if __name__ == "__main__":
    sys.exit(main())
