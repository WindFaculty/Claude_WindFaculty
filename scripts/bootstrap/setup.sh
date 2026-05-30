#!/usr/bin/env bash
# Bash Environment Bootstrap Script for Claude_WindFaculty
set -e

# ANSI Color Codes
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}Claude WindFaculty Unix Bootstrapper     ${NC}"
echo -e "${CYAN}=========================================${NC}"

# 1. Check Python installation
echo -e "${YELLOW}[1/5] Checking Python availability...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python is not installed or found in PATH.${NC}" >&2
    exit 1
fi
echo -e "Found $($PYTHON_CMD --version) as ${GREEN}$PYTHON_CMD${NC}"

# 2. Check and establish Virtual Environment
echo -e "${YELLOW}[2/5] Establishing Python Virtual Environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${GRAY}Creating new virtual environment in .venv...${NC}"
    $PYTHON_CMD -m venv .venv
    echo -e "${GREEN}Virtual environment established.${NC}"
else
    echo -e "${GREEN}Existing .venv directory detected.${NC}"
fi

# 3. Upgrade pip and install dependencies
echo -e "${YELLOW}[3/5] Installing essential workspace dependencies...${NC}"
VENV_PYTHON="./.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="python"
fi

echo -e "${GRAY}Upgrading pip...${NC}"
$VENV_PYTHON -m pip install --upgrade pip --quiet || true

echo -e "${GRAY}Installing pytest...${NC}"
$VENV_PYTHON -m pip install pytest --quiet || true

echo -e "${GRAY}Installing boto3 for AWS Bedrock integration...${NC}"
$VENV_PYTHON -m pip install boto3 --quiet || true

echo -e "${GRAY}Installing optional Semble code search (opt-in)...${NC}"
$VENV_PYTHON -m pip install "semble[mcp]" --quiet || true

echo -e "${GREEN}Dependencies successfully updated.${NC}"

# 4. Generate local .env
echo -e "${YELLOW}[4/5] Syncing environment configurations...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${GRAY}Generating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file successfully created.${NC}"
else
    echo -e "${GREEN}Existing .env file detected.${NC}"
fi

# 5. Run verify script
echo -e "${YELLOW}[5/5] Executing environment validation suite...${NC}"
if $VENV_PYTHON scripts/bootstrap/verify_environment.py; then
    echo -e "${CYAN}=========================================${NC}"
    echo -e "${GREEN}BOOTSTRAP SUCCESSFUL: Môi trường đã sẵn sàng!${NC}"
    echo -e "${GRAY}Run tests using: source .venv/bin/activate && pytest${NC}"
    echo -e "${CYAN}=========================================${NC}"
    exit 0
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}BOOTSTRAP FAILED: Gặp lỗi khi verify môi trường!${NC}"
    echo -e "${RED}=========================================${NC}"
    exit 1
fi
