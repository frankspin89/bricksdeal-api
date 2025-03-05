#!/bin/bash

# Script to handle Python environment setup and run the extract command
# This avoids having to manually set up the environment each time

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists, create if it doesn't
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install required packages if not already installed
if ! python3 -c "import PIL" &> /dev/null; then
    echo "Installing required packages..."
    pip install pillow boto3 requests python-dotenv
    pip install -e .
fi

# Parse command line arguments
LIMIT=""
MINIFIGS_ONLY=""
USE_PROXIES=""
PROXIES_FILE="input/proxies.csv"

while [[ $# -gt 0 ]]; do
    case $1 in
        --limit)
            LIMIT="--limit $2"
            shift 2
            ;;
        --all)
            MINIFIGS_ONLY=""
            shift
            ;;
        --minifigs-only)
            MINIFIGS_ONLY="--minifigs-only"
            shift
            ;;
        --use-proxies)
            USE_PROXIES="--use-proxies"
            shift
            ;;
        --proxies-file)
            PROXIES_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# If no specific options were provided, default to minifigs-only and use-proxies
if [ -z "$MINIFIGS_ONLY" ]; then
    MINIFIGS_ONLY="--minifigs-only"
fi

if [ -z "$USE_PROXIES" ]; then
    USE_PROXIES="--use-proxies"
fi

# Create necessary directories
mkdir -p input/lego-catalog-extracted
mkdir -p input/lego-catalog-processed
mkdir -p output/catalog-images
mkdir -p output/database

# Run the extract command
echo "Running extract command with options: $LIMIT $MINIFIGS_ONLY $USE_PROXIES --proxies-file $PROXIES_FILE"
python3 -m bricks_deal_crawl.catalog.extract --process-images $MINIFIGS_ONLY $LIMIT $USE_PROXIES --proxies-file $PROXIES_FILE

# Deactivate virtual environment
deactivate 