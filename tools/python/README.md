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

## Comprehensive Command Analysis

### Main CLI Commands

The Bricks Deal Python tools provide a comprehensive command-line interface with the following main commands:

#### 1. `extract-catalog`: Extract and Process LEGO Catalog Data

This command extracts LEGO catalog data from various sources and processes it for use in the Bricks Deal system.

**Options:**
- `--extract-only`: Only extract .gz files without processing images
- `--process-images`: Process images without extracting .gz files
- `--update-csv`: Update CSV files with new image URLs
- `--limit NUMBER`: Limit the number of images to process
- `--minifigs-only`: Process only minifigure images
- `--test`: Run test function for multiple images
- `--use-proxies`: Use proxy rotation for image downloads
- `--proxies-file FILE`: File containing proxy URLs (default: input/proxies.csv)
- `--start-index NUMBER`: Start index for batch processing (default: 0)
- `--batch-size NUMBER`: Batch size for processing (0 means process all)
- `--rebuild-mapping`: Rebuild image mapping from catalog-images directory
- `--force-upload`: Force upload all images to Cloudflare R2 when rebuilding mapping
- `--test-proxy`: Test proxy configuration
- `--force-own-ip`: Allow using your own IP address if no proxy is available
- `--dry-run`: Skip downloading images but perform all other operations
- `--validate-urls`: Validate image URLs in the mapping file
- `--validate-all`: Validate all URLs, not just Cloudflare ones
- `--verify-r2`: Verify that all objects in the R2 bucket are mapped in the CSV files
- `--cleanup-local`: Remove local files that have been successfully uploaded to R2
- `--continue`: Continue processing from where you left off
- `--show-progress`: Show current processing progress

**What happens when executed:**
1. The script loads configuration from environment variables
2. If extracting, it downloads and extracts LEGO catalog data from source files
3. If processing images, it:
   - Downloads images from LEGO's servers (using proxies if specified)
   - Optimizes images for web use
   - Uploads images to Cloudflare R2 storage
   - Updates image URLs in CSV files
4. Progress is tracked and can be resumed using the `--continue` option
5. Various validation and verification steps can be performed

**Example usage:**
```bash
# Extract and process minifigure images with proxy rotation
bricks-deal extract-catalog --process-images --minifigs-only --use-proxies

# Update CSV files with new image URLs for minifigures
bricks-deal extract-catalog --update-csv --minifigs-only

# Process a batch of 50 minifigures starting from index 100
bricks-deal extract-catalog --process-images --minifigs-only --start-index 100 --batch-size 50

# Validate all image URLs in the mapping file
bricks-deal extract-catalog --validate-urls --validate-all
```

#### 2. `continue-extract`: Continue Extraction from Previous Point

This command allows you to continue extracting and processing LEGO catalog data from where you left off, using a progress tracking file.

**Options:**
- `--type {minifigs,sets}`: Type of items to process (default: minifigs)
- `--batch-size NUMBER`: Number of items to process in this batch (default: 100)
- `--no-proxies`: Disable proxy rotation for image downloads
- `--proxies-file FILE`: File containing proxy URLs
- `--no-update-csv`: Don't update CSV files with new image URLs
- `--reset`: Reset progress tracking and start from the beginning
- `--reset-type {minifigs,sets}`: Reset progress for a specific item type
- `--show`: Show current progress without running extraction

**What happens when executed:**
1. The script loads the current progress from a tracking file
2. If `--show` is specified, it displays the current progress and exits
3. If `--reset` or `--reset-type` is specified, it resets the progress tracking
4. Otherwise, it runs the extraction process from the last processed index
5. After processing the batch, it updates the progress tracking file

**Example usage:**
```bash
# Process the next batch of 100 minifigs
bricks-deal continue-extract

# Process the next batch of 200 sets
bricks-deal continue-extract --type sets --batch-size 200

# Show current progress without processing
bricks-deal continue-extract --show

# Reset progress tracking for minifigs
bricks-deal continue-extract --reset-type minifigs
```

#### 3. `interactive`: Interactive CLI Menu

This command starts an interactive menu-driven interface that guides you through all available options.

**What happens when executed:**
1. The script displays a menu with all available commands
2. You can navigate through the menu and select options
3. The script executes the selected command with the specified options

**Example usage:**
```bash
bricks-deal interactive
```

#### 4. `update-prices`: Update LEGO Product Prices

This command updates prices for LEGO products in the database.

**Options:**
- `--set-num SET_NUM`: LEGO set number to update
- `--limit NUMBER`: Limit the number of sets to update
- `--offset NUMBER`: Start updating from this offset

**What happens when executed:**
1. The script connects to the database
2. It fetches current price data from external sources
3. It updates the prices in the database
4. It generates reports on price changes

**Example usage:**
```bash
# Update prices for all sets
bricks-deal update-prices

# Update price for a specific set
bricks-deal update-prices --set-num 10423-1

# Update prices for 100 sets starting from offset 200
bricks-deal update-prices --limit 100 --offset 200
```

#### 5. `setup-db`: Set Up the LEGO Catalog Database

This command sets up the database schema for the LEGO catalog.

**Options:**
- `--clean`: Clean the database before setup
- `--local`: Set up the local database
- `--remote`: Set up the remote database

**What happens when executed:**
1. If `--clean` is specified, it drops existing tables
2. It creates the necessary database tables
3. It sets up indexes and constraints
4. It initializes any required data

**Example usage:**
```bash
# Set up the database
bricks-deal setup-db

# Clean and set up the database
bricks-deal setup-db --clean

# Set up both local and remote databases
bricks-deal setup-db --local --remote
```

#### 6. `export`: Export LEGO Catalog Data

This command exports LEGO catalog data to various targets.

**Options:**
- `--target {cloudflare,d1}`: Export target (required)
- `--sets`: Export sets data
- `--prices`: Export prices data
- `--themes`: Export themes data

**What happens when executed:**
1. The script connects to the database
2. It extracts the requested data
3. It formats the data for the specified target
4. It uploads the data to the target (Cloudflare R2 or D1)

**Example usage:**
```bash
# Export to Cloudflare R2 and D1
bricks-deal export --target cloudflare

# Export to D1 database only
bricks-deal export --target d1

# Export only sets data to Cloudflare
bricks-deal export --target cloudflare --sets
```

#### 7. `clean`: Clean Cloudflare Resources

This command cleans Cloudflare R2 bucket and D1 database.

**Options:**
- `--r2`: Clean R2 bucket
- `--d1`: Clean D1 database
- `--force`: Force cleaning without confirmation
- `--backup`: Create a backup before cleaning

**What happens when executed:**
1. If `--backup` is specified, it creates a backup of the data
2. If `--r2` is specified, it cleans the R2 bucket
3. If `--d1` is specified, it cleans the D1 database
4. If neither is specified, it cleans both

**Example usage:**
```bash
# Clean both R2 and D1 with confirmation
bricks-deal clean

# Clean only R2 bucket without confirmation
bricks-deal clean --r2 --force

# Create a backup before cleaning D1 database
bricks-deal clean --d1 --backup
```

#### 8. `cleanup`: Clean Up Temporary Files

This command cleans up temporary files and directories.

**Options:**
- `--dry-run`: Show what would be done without actually doing it
- `--backup`: Backup files before removing them
- `--deep-clean`: Perform a deeper cleanup, removing temporary files
- `--force`: Force cleaning without confirmation

**What happens when executed:**
1. The script identifies temporary files and directories
2. If `--backup` is specified, it creates backups
3. If `--dry-run` is specified, it only shows what would be deleted
4. Otherwise, it deletes the identified files and directories

**Example usage:**
```bash
# Show what would be cleaned up
bricks-deal cleanup --dry-run

# Perform a deep cleanup with backup
bricks-deal cleanup --deep-clean --backup

# Force cleanup without confirmation
bricks-deal cleanup --force
```

#### 9. `clean-backups`: Clean Old Backup Directories

This command cleans old backup directories, keeping only the most recent ones.

**Options:**
- `--max-backups NUMBER`: Maximum number of backups to keep (default: 5)
- `--dry-run`: Show what would be done without actually doing it
- `--force`: Force cleaning without confirmation
- `--backup-dir DIRECTORY`: Backup directory (default: backups)

**What happens when executed:**
1. The script identifies all backup directories
2. It sorts them by creation date
3. It keeps the most recent ones (specified by `--max-backups`)
4. It deletes the older ones

**Example usage:**
```bash
# Clean old backups, keeping the 3 most recent
bricks-deal clean-backups --max-backups 3

# Show what backups would be deleted
bricks-deal clean-backups --dry-run

# Force cleaning without confirmation
bricks-deal clean-backups --force
```

#### 10. `help`: Show Detailed Help Information

This command shows detailed help and usage information.

**Options:**
- `--command COMMAND`: Show help for a specific command

**What happens when executed:**
1. The script displays the Bricks Deal logo
2. It shows detailed help for all commands or a specific command
3. It provides examples of common workflows

**Example usage:**
```bash
# Show general help
bricks-deal help

# Show help for a specific command
bricks-deal help --command extract-catalog
```

### Helper Scripts

The repository includes several helper scripts to simplify common operations:

#### 1. `run_extract.sh`

This script handles Python environment setup and runs the extract command.

**Options:**
- `--limit NUMBER`: Limit the number of images to process
- `--all`: Process all LEGO items (not just minifigs)
- `--minifigs-only`: Process only minifigure images (default)
- `--use-proxies`: Use proxy rotation for image downloads (default)
- `--proxies-file FILE`: File containing proxy URLs

**What happens when executed:**
1. The script checks if the virtual environment exists and creates it if needed
2. It activates the virtual environment
3. It installs required packages if not already installed
4. It creates necessary directories
5. It runs the extract command with the specified options

**Example usage:**
```bash
# Run with default options (minifigs-only and use-proxies)
./run_extract.sh

# Run with custom options
./run_extract.sh --limit 100 --all
```

#### 2. `process_all_minifigs.sh`

This script processes all minifigures in batches.

**What happens when executed:**
1. The script activates the virtual environment if it exists
2. It creates necessary directories
3. It processes all minifigures in batches of 100
4. It sleeps briefly between batches to avoid overwhelming the system

**Example usage:**
```bash
# Process all minifigures in batches of 100
./process_all_minifigs.sh
```

#### 3. `setup_environment.sh`

This script sets up the Python environment with the correct Python version.

**What happens when executed:**
1. The script checks for compatible Python versions (3.8-3.12 recommended)
2. It creates a virtual environment with the best available Python version
3. It activates the virtual environment
4. It installs required packages
5. It provides information about the setup and how to use the tools

**Example usage:**
```bash
# Set up the environment
./setup_environment.sh
```

#### 4. `continue_extract.py`

This script allows you to process items in batches and automatically continue from where you left off.

**Options:**
- `--type {minifigs,sets}`: Type of items to process (default: minifigs)
- `--batch-size NUMBER`: Number of items to process in this batch (default: 100)
- `--no-proxies`: Disable proxy rotation for image downloads
- `--proxies-file FILE`: File containing proxy URLs
- `--no-update-csv`: Don't update CSV files with new image URLs
- `--reset`: Reset progress tracking and start from the beginning
- `--reset-type {minifigs,sets}`: Reset progress for a specific item type
- `--show`: Show current progress without running extraction

**What happens when executed:**
1. The script loads the current progress from a tracking file
2. If `--show` is specified, it displays the current progress and exits
3. If `--reset` or `--reset-type` is specified, it resets the progress tracking
4. Otherwise, it runs the extraction process from the last processed index
5. After processing the batch, it updates the progress tracking file

**Example usage:**
```bash
# Process the next batch of 100 minifigs
./continue_extract.py

# Process the next batch of 200 sets
./continue_extract.py --type sets --batch-size 200

# Show current progress without processing
./continue_extract.py --show

# Reset progress tracking
./continue_extract.py --reset
```

### Testing Scripts

The repository includes scripts for testing various components:

#### 1. `test_oxylabs.py`

This script tests the Oxylabs proxy configuration.

**What happens when executed:**
1. The script loads Oxylabs credentials from environment variables
2. It tests different proxy configurations (datacenter and country-specific)
3. It reports the results of each test

**Example usage:**
```bash
# Test Oxylabs proxy configuration
./test_oxylabs.py
```

#### 2. `simple_test.py`

This script performs a simple test of the proxy configuration.

**What happens when executed:**
1. The script loads Oxylabs credentials from environment variables
2. It makes a request to a test URL using the proxy
3. It reports the result of the test

**Example usage:**
```bash
# Run a simple proxy test
./simple_test.py
```

## Directory Structure

- `input/`: Input data files and proxies
  - `lego-catalog/`: Raw LEGO catalog data
  - `lego-catalog-extracted/`: Extracted catalog data
  - `lego-catalog-processed/`: Processed catalog data
  - `proxies.csv`: List of proxy servers for image downloading
  - `extract_progress.json`: Progress tracking file for batch processing
- `output/`: Output files and processed data
  - `catalog-images/`: Processed catalog images
  - `database/`: Database files and exports
- `bricks_deal_crawl/`: Main package
  - `catalog/`: Catalog extraction and processing
    - `extract.py`: Main extraction and processing logic
    - `continue_extract.py`: Continuation of extraction from previous point
    - `lego_data.py`: LEGO data handling utilities
  - `database/`: Database setup and management
  - `export/`: Export functionality
  - `utils/`: Utility functions and helpers
  - `scrapers/`: Web scrapers for data collection
  - `main.py`: Main entry point for the package
  - `cli.py`: Command-line interface implementation

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

## Common Workflows

### Initial Setup

1. Set up the Python environment:
   ```bash
   ./setup_environment.sh
   ```

2. Set up the database:
   ```bash
   bricks-deal setup-db
   ```

3. Extract and process catalog data:
   ```bash
   bricks-deal extract-catalog --process-images
   ```

4. Update prices:
   ```bash
   bricks-deal update-prices
   ```

### Batch Processing

1. Process minifigures in batches:
   ```bash
   ./process_all_minifigs.sh
   ```

2. Or use the continue-extract command:
   ```bash
   bricks-deal continue-extract
   ```

3. Check progress:
   ```bash
   bricks-deal continue-extract --show
   ```

### Maintenance

1. Clean up temporary files:
   ```bash
   bricks-deal cleanup
   ```

2. Clean old backups:
   ```bash
   bricks-deal clean-backups
   ```

3. Validate image URLs:
   ```bash
   bricks-deal extract-catalog --validate-urls
   ```

## Troubleshooting

### Proxy Issues

If you encounter issues with proxies:

1. Test your proxy configuration:
   ```bash
   ./test_oxylabs.py
   ```

2. Try a simple test:
   ```bash
   ./simple_test.py
   ```

3. Check your environment variables:
   ```bash
   echo $OXYLABS_USERNAME
   echo $OXYLABS_PASSWORD
   ```

### Image Processing Issues

If image processing fails:

1. Try with a smaller batch size:
   ```bash
   bricks-deal extract-catalog --process-images --batch-size 10
   ```

2. Use the `--dry-run` option to test without downloading:
   ```bash
   bricks-deal extract-catalog --process-images --dry-run
   ```

3. Validate existing URLs:
   ```bash
   bricks-deal extract-catalog --validate-urls
   ```

### Database Issues

If you encounter database issues:

1. Clean and set up the database again:
   ```bash
   bricks-deal setup-db --clean
   ```

2. Check database files in the output/database directory

For more detailed documentation, see the main [README.md](../../README.md) and [WORKFLOW.md](../../WORKFLOW.md) files. 