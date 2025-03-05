#!/bin/bash

# Script to process all minifigures in batches
# This script will process the entire dataset of minifigures in batches of 100

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Create necessary directories
mkdir -p input/lego-catalog-extracted
mkdir -p input/lego-catalog-processed
mkdir -p output/catalog-images
mkdir -p output/database

# Configuration
BATCH_SIZE=100
TOTAL_ROWS=15383
USE_PROXIES="--use-proxies"

# Process all batches
for ((i=0; i<TOTAL_ROWS; i+=BATCH_SIZE)); do
    echo "========================================================"
    echo "Processing batch $i to $((i+BATCH_SIZE-1)) of $TOTAL_ROWS"
    echo "========================================================"
    
    # Run the extract command for this batch
    python3 -m bricks_deal_crawl.catalog.extract --process-images --minifigs-only --start-index $i --batch-size $BATCH_SIZE $USE_PROXIES
    
    # Sleep for a moment to avoid overwhelming the system
    sleep 2
done

echo "All batches processed successfully!"

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
    echo "Deactivated virtual environment"
fi 