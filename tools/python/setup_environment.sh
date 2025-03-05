#!/bin/bash

# Script to set up the Python environment with the correct Python version
# This script will check for compatible Python versions and set up the environment

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}Bricks Deal Python Environment Setup${NC}"
echo "========================================"

# Check for Python versions
echo -e "${YELLOW}Checking for Python versions...${NC}"

# Try different Python commands
PYTHON_CMD=""
PYTHON_VERSION=""
PYTHON_WARNING=""

for cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd --version 2>&1 | awk '{print $2}')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        
        if [[ "$major" == "3" ]]; then
            if [[ "$minor" -ge 8 && "$minor" -le 12 ]]; then
                PYTHON_CMD=$cmd
                PYTHON_VERSION=$version
                echo -e "${GREEN}Found recommended Python version: $PYTHON_VERSION ($PYTHON_CMD)${NC}"
                break
            elif [[ "$minor" -ge 13 ]]; then
                # Store Python 3.13+ as a fallback but continue looking for 3.8-3.12
                if [[ -z "$PYTHON_CMD" ]]; then
                    PYTHON_CMD=$cmd
                    PYTHON_VERSION=$version
                    PYTHON_WARNING="WARNING: Python $PYTHON_VERSION is newer than the recommended range (3.8-3.12). Some packages may not be fully compatible."
                    echo -e "${YELLOW}Found Python $version ($cmd) - newer than recommended range (3.8-3.12)${NC}"
                fi
            else
                echo -e "${YELLOW}Found Python $version ($cmd) - older than recommended minimum (3.8)${NC}"
            fi
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo -e "${RED}No compatible Python version found. Please install Python 3.8 or newer.${NC}"
    exit 1
fi

if [[ -n "$PYTHON_WARNING" ]]; then
    echo -e "${YELLOW}$PYTHON_WARNING${NC}"
    echo -e "${YELLOW}Proceeding with Python $PYTHON_VERSION, but you may encounter compatibility issues.${NC}"
    echo -e "${YELLOW}Consider installing Python 3.8-3.12 for best compatibility.${NC}"
    
    # Ask for confirmation
    read -p "Continue with Python $PYTHON_VERSION? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Setup aborted.${NC}"
        exit 1
    fi
fi

# Check if virtual environment exists, create if it doesn't
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment with $PYTHON_CMD $PYTHON_VERSION...${NC}"
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create virtual environment. Please install the venv module:${NC}"
        echo -e "${YELLOW}$PYTHON_CMD -m pip install --user virtualenv${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
pip install --upgrade pip
pip install -e .

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install packages.${NC}"
    deactivate
    exit 1
fi

echo -e "${GREEN}Environment setup complete!${NC}"
echo -e "${YELLOW}Python version: $PYTHON_VERSION${NC}"
echo -e "${YELLOW}Virtual environment: $(which python)${NC}"
echo -e "${YELLOW}Installed packages:${NC}"
pip list

echo -e "${GREEN}You can now run the scripts with:${NC}"
echo -e "${BLUE}source venv/bin/activate${NC}"
echo -e "${BLUE}python -m bricks_deal_crawl.main [command] [options]${NC}"
echo -e "or use the helper scripts:"
echo -e "${BLUE}./run_extract.sh [options]${NC}"
echo -e "${BLUE}./process_all_minifigs.sh${NC}"

# Keep the virtual environment active
echo -e "${YELLOW}Virtual environment is now active.${NC}" 