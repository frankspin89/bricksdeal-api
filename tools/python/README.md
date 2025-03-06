# Bricks Deal Python Tools

This directory contains the Python tools for the Bricks Deal project, providing a comprehensive suite of utilities for LEGO catalog data extraction, processing, and management.

## Requirements

- **Python**: Version 3.8 to 3.12 recommended (Python 3.13+ may have compatibility issues with some packages)
- **Operating Systems**: macOS, Linux, or Windows with WSL

## Features

- **Catalog Data Extraction**: Extract LEGO catalog data from various sources
- **Image Processing**: Download, optimize, and generate SEO-friendly URLs for LEGO images
- **Database Management**: Set up, clean, and manage the LEGO catalog database
- **Price Updates**: Track and update prices for LEGO sets
- **Export Functionality**: Export data to Cloudflare R2 and D1 for web serving
- **Cleanup Utilities**: Manage temporary files and backups

## Installation

```bash
# From the tools/python directory

# On macOS/Linux where python3 is the command (not python)
python3 -m venv venv
source venv/bin/activate

# On systems where python is the command
# python -m venv venv
# source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .
```

## Troubleshooting Python Version Issues

If you're experiencing issues with Python versions:

1. **Check your Python version**:
   ```bash
   python3 --version  # or python --version
   ```

2. **For Python 3.13+**:
   Some packages may not be fully compatible with Python 3.13+. Consider using Python 3.8-3.12.

3. **Command not found errors**:
   - If `python` command is not found, use `python3` instead
   - Update the shell scripts by editing them:
     ```bash
     # Change python to python3 in run_extract.sh and process_all_minifigs.sh
     sed -i '' 's/python /python3 /g' run_extract.sh process_all_minifigs.sh
     ```

## Command Overview

The CLI provides the following main commands:

- `extract-catalog`: Extract and process LEGO catalog data
- `continue-extract`: Continue extraction from where you left off
- `interactive`: Start interactive CLI menu with guided options
- `update-prices`: Update prices for LEGO products
- `setup-db`: Set up the LEGO catalog database
- `export`: Export LEGO catalog data to various targets
- `clean`: Clean Cloudflare R2 bucket and D1 database
- `cleanup`: Clean up temporary files and directories
- `clean-backups`: Clean old backup directories
- `help`: Show detailed help and usage information

## Usage Examples

### Catalog Extraction

```bash
# Extract catalog data with image processing
python3 -m bricks_deal_crawl.main extract-catalog --process-images

# Extract only minifigure data with a limit
python3 -m bricks_deal_crawl.main extract-catalog --process-images --minifigs-only --limit 100

# Use proxies for extraction
python3 -m bricks_deal_crawl.main extract-catalog --process-images --use-proxies --proxies-file input/proxies.csv

# Update CSV files with new image URLs
python3 -m bricks_deal_crawl.main extract-catalog --update-csv --minifigs-only --use-proxies

# Batch processing with start index and batch size
python3 -m bricks_deal_crawl.main extract-catalog --process-images --minifigs-only --start-index 100 --batch-size 50
```

### Continuous Batch Processing

The `continue_extract.py` script allows you to process items in batches and automatically continue from where you left off:

```bash
# Process the next batch of 100 minifigs
./continue_extract.py

# Process the next batch of 200 minifigs
./continue_extract.py --batch-size 200

# Process sets instead of minifigs
./continue_extract.py --type sets

# Show current progress without processing
./continue_extract.py --show

# Reset progress tracking to start from the beginning
./continue_extract.py --reset

# Reset progress for a specific item type
./continue_extract.py --reset-type minifigs
```

You can also use the built-in CLI command for continuous extraction:

```bash
# Process the next batch of 100 minifigs
bricks-deal continue-extract

# Process the next batch of 200 minifigs
bricks-deal continue-extract --batch-size 200

# Process sets instead of minifigs
bricks-deal continue-extract --type sets

# Show current progress without processing
bricks-deal continue-extract --show

# Reset progress tracking to start from the beginning
bricks-deal continue-extract --reset

# Reset progress for a specific item type
bricks-deal continue-extract --reset-type minifigs
```

### Price Updates

```bash
# Update prices for all sets
python3 -m bricks_deal_crawl.main update-prices

# Update price for a specific set
python3 -m bricks_deal_crawl.main update-prices --set-num 10423-1
```

### Database Management

```bash
# Set up the database
python3 -m bricks_deal_crawl.main setup-db

# Clean the database before setup
python3 -m bricks_deal_crawl.main setup-db --clean
```

### Data Export

```bash
# Export to Cloudflare R2 and D1
python3 -m bricks_deal_crawl.main export --target cloudflare

# Export to D1 database only
python3 -m bricks_deal_crawl.main export --target d1
```

### Cleanup Operations

```bash
# Clean Cloudflare resources
python3 -m bricks_deal_crawl.main clean --r2 --d1

# Clean up temporary files
python3 -m bricks_deal_crawl.main cleanup --deep-clean

# Clean old backups
python3 -m bricks_deal_crawl.main clean-backups --max-backups 5
```

## Helper Scripts

The repository includes several helper scripts to simplify common operations:

### run_extract.sh

This script handles Python environment setup and runs the extract command:

```bash
# Run with default options (minifigs-only and use-proxies)
./run_extract.sh

# Run with custom options
./run_extract.sh --limit 100 --all
```

### process_all_minifigs.sh

This script processes all minifigures in batches:

```bash
# Process all minifigures in batches of 100
./process_all_minifigs.sh
```

### setup_environment.sh

This script sets up the Python environment with the correct Python version:

```bash
# Set up the environment
./setup_environment.sh
```

## Directory Structure

- `input/`: Input data files and proxies
  - `lego-catalog/`: Raw LEGO catalog data
  - `lego-catalog-extracted/`: Extracted catalog data
  - `lego-catalog-processed/`: Processed catalog data
- `output/`: Output files and processed data
  - `catalog-images/`: Processed catalog images
  - `database/`: Database files and exports
- `bricks_deal_crawl/`: Main package
  - `catalog/`: Catalog extraction and processing
  - `database/`: Database setup and management
  - `export/`: Export functionality
  - `utils/`: Utility functions and helpers
  - `scrapers/`: Web scrapers for data collection

## Environment Variables

The tools use the following environment variables:

- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID
- `CLOUDFLARE_ACCESS_KEY_ID`: Cloudflare R2 access key ID
- `CLOUDFLARE_SECRET_ACCESS_KEY`: Cloudflare R2 secret access key
- `CLOUDFLARE_R2_BUCKET`: Cloudflare R2 bucket name (default: lego-images)
- `CLOUDFLARE_DOMAIN`: Cloudflare domain (default: images.bricksdeal.com)
- `OXYLABS_USERNAME`: Oxylabs proxy username
- `OXYLABS_PASSWORD`: Oxylabs proxy password
- `OXYLABS_ENDPOINT`: Oxylabs proxy endpoint (default: dc.oxylabs.io)
- `OXYLABS_PORTS`: Comma-separated list of Oxylabs proxy ports

For more detailed documentation, see the main [README.md](../../README.md) and [WORKFLOW.md](../../WORKFLOW.md) files.

### Interactive Mode

The CLI provides an interactive menu-driven interface that guides you through all available options:

```bash
# Start the interactive CLI menu
bricks-deal interactive
```

This will display a colorful menu with the following options:

1. **Extract Catalog**: Extract and process LEGO catalog data
   - Extract Catalog Data
   - Process Images
   - Update CSV Files
   - Continue Extraction
   - Show Extraction Progress
   - Reset Extraction Progress

2. **Update Prices**: Update prices for LEGO products
   - Update All Prices
   - Update Specific Set

3. **Database Management**: Set up and manage the LEGO catalog database
   - Setup Database
   - Clean Database

4. **Export Data**: Export LEGO catalog data to various targets
   - Export to Cloudflare
   - Export to D1 Only

5. **Cleanup Operations**: Clean up resources and temporary files
   - Clean Cloudflare Resources
   - Clean Temporary Files
   - Clean Old Backups

6. **Help**: Show detailed help and usage information

The interactive mode is perfect for users who don't want to remember all the command-line options and prefer a guided approach.

### Price Updates 