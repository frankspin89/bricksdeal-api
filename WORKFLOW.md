# LEGO Database Workflow

## Project Structure

The project has been restructured to follow a more organized and maintainable pattern:

```
bricks-deal-crawl2/
├── README.md
├── WORKFLOW.md
├── requirements.txt
├── setup.py                # Package installation
├── .gitignore
├── scripts/                # Shell scripts and utilities
│   ├── bricks-deal         # Main command-line script
│   └── check_prices.sh
├── src/                    # Main Python package
│   ├── main.py             # Main entry point
│   ├── bricks_deal_crawl/  # Main package directory
│   │   ├── __init__.py     # Package documentation
│   │   ├── scrapers/       # Web scraping modules
│   │   ├── catalog/        # Catalog data processing
│   │   ├── database/       # Database operations
│   │   ├── export/         # Export functionality
│   │   └── utils/          # Utility functions
├── tests/                  # Unit tests
├── input/                  # Input data
└── output/                 # Output data
```

## Initial Setup

1. **Install the package in development mode**:

   ```bash
   pip install -e .
   ```

2. **Extract and prepare catalog data**:

   ```bash
   # Using the command-line script
   bricks-deal extract-catalog

   # Additional options:
   bricks-deal extract-catalog --process-images            # Only process images
   bricks-deal extract-catalog --update-csv                # Only update CSV files
   bricks-deal extract-catalog --process-images --limit 100      # Process only 100 images
   bricks-deal extract-catalog --process-images --minifigs-only  # Process only minifigure images
   ```

3. **Create a clean SQLite database**:

   ```bash
   bricks-deal setup-db --clean
   ```

4. **Setup the database**:

   ```bash
   bricks-deal setup-db
   ```

5. **Export to Cloudflare D1 (one-time setup)**:

   ```bash
   bricks-deal export --target d1
   ```

## Regular Updates

1. **Update prices**:

   ```bash
   # Update all prices
   bricks-deal update-prices

   # For a specific set
   bricks-deal update-prices --set-num 10353
   ```

2. **Update Cloudflare D1**:

   ```bash
   bricks-deal export --target d1
   ```

3. **Deploy to Cloudflare**:

   ```bash
   wrangler deploy
   ```

## Maintenance

1. **Clean up temporary files**:

   ```bash
   # Basic cleanup
   bricks-deal cleanup

   # Cleanup without confirmation
   bricks-deal cleanup --force

   # Dry run (show what would be cleaned without actually cleaning)
   bricks-deal cleanup --dry-run

   # Deep clean (remove additional temporary files)
   bricks-deal cleanup --deep-clean

   # Backup important files before cleaning
   bricks-deal cleanup --backup
   ```

2. **Update processed URLs**:

   ```bash
   bricks-deal update-processed-urls
   ```

3. **Clean Cloudflare resources**:

   ```bash
   # Clean both R2 bucket and D1 database
   bricks-deal clean

   # Clean only R2 bucket
   bricks-deal clean --r2

   # Clean only D1 database
   bricks-deal clean --d1

   # Clean without confirmation
   bricks-deal clean --force
   ```

4. **Get help and documentation**:

   ```bash
   # Show detailed help with all commands and workflows
   bricks-deal help

   # Show help for a specific command
   bricks-deal [command] --help
   ```

## Data Preparation Details

### Catalog Data Extraction

The catalog module performs three main tasks:

1. **Extract .gz files**: Converts compressed catalog files to plain CSV files
2. **Process images**: Downloads, optimizes, and uploads images to Cloudflare R2
3. **Update CSV files**: Updates the CSV files with the new Cloudflare image URLs

This ensures that all data is self-contained and doesn't rely on external image sources.

The module supports several options:

- `--process-images`: Process images without extracting .gz files
- `--update-csv`: Update CSV files with new image URLs
- `--limit N`: Limit the number of images to process (useful for testing)
- `--minifigs-only`: Process only minifigure images

Image processing includes:

- Downloading images from external sources
- Optimizing images (resizing, compression)
- Uploading to Cloudflare R2 with proper caching headers
- Organizing images in folders by type (set/minifig)
- Creating a mapping between original and processed image URLs
- Generating SEO-friendly filenames for better search engine visibility

### Database Creation

The database module creates a fresh SQLite database with the proper schema, including:

- Tables for sets, themes, minifigures, images, etc.
- Proper relationships between tables
- Indexes for better performance

### Cloudflare Integration

The project uses three Cloudflare services:

- **D1**: SQL database for storing structured data
- **R2**: Object storage for images
- **Workers**: Serverless functions for the API

## Module Documentation

The project includes comprehensive documentation for all modules:

### Main Package

The `bricks_deal_crawl` package provides tools for processing LEGO catalog data and managing prices.

### Catalog Module

Handles LEGO catalog data extraction, processing, and management, including:

- SEO-friendly image URL generation
- CSV data extraction and processing
- Image optimization and transformation

### Database Module

Manages the setup and maintenance of the LEGO catalog database, including:

- Database setup and initialization
- Data cleaning and normalization
- Database enrichment with additional data

### Export Module

Provides functionality for exporting LEGO catalog data to various targets:

- Cloudflare R2 for image storage
- Cloudflare D1 for database storage
- Direct D1 updates for efficient data management

### Scrapers Module

Contains web scraping modules for LEGO product data:

- LEGO direct website scraping
- New product URL scraping
- Proxy rotation to avoid IP blocks
- Parallel processing for efficiency

### Utils Module

Provides utility functions for various tasks:

- Price updates and tracking
- Temporary file cleanup
- URL processing and management

## Maintenance Commands

### Cleanup Commands

The project includes several cleanup commands to help maintain a clean workspace and manage Cloudflare resources.

#### Basic Cleanup

To clean up temporary files and directories:

```bash
bricks-deal cleanup
```

This will prompt for confirmation before deleting files.

#### Cleanup without Confirmation

To skip the confirmation prompt:

```bash
bricks-deal cleanup --force
```

#### Dry Run

To see what would be deleted without actually deleting anything:

```bash
bricks-deal cleanup --dry-run
```

#### Deep Clean

To perform a deep clean (including node_modules):

```bash
bricks-deal cleanup --deep-clean
```

#### Backup Before Cleaning

To create a backup before cleaning:

```bash
bricks-deal cleanup --backup
```

This will create a backup of important files in the `backups` directory with a timestamp. Sensitive information in configuration files will be automatically redacted.

#### Managing Backups

To limit the number of backups kept:

```bash
bricks-deal cleanup --backup --max-backups 3
```

This will keep only the 3 most recent backups and remove older ones.

#### Cleaning Old Backups

A dedicated command is available to clean old backups:

```bash
bricks-deal clean-backups
```

This will keep the 5 most recent backups and remove older ones.

To specify the maximum number of backups to keep:

```bash
bricks-deal clean-backups --max-backups 3
```

To see what would be deleted without actually deleting:

```bash
bricks-deal clean-backups --dry-run
```

To skip the confirmation prompt:

```bash
bricks-deal clean-backups --force
```

To specify a different backup directory:

```bash
bricks-deal clean-backups --backup-dir my-backups
```

### Cloudflare Resource Cleaning

To clean Cloudflare resources (R2 bucket and D1 database):

```bash
bricks-deal clean
```

This will prompt for confirmation before cleaning.

#### Clean Only R2 Bucket

```bash
bricks-deal clean --r2
```

#### Clean Only D1 Database

```bash
bricks-deal clean --d1
```

#### Clean Without Confirmation

```bash
bricks-deal clean --force
```

#### Backup Before Cleaning Cloudflare Resources

```bash
bricks-deal clean --backup
```

This will create a backup of important configuration files in the `backups` directory with a timestamp. Sensitive information in configuration files will be automatically redacted.

### Backup Security

The backup functionality includes security features to protect sensitive information:

1. **Dedicated Backup Directory**: All backups are stored in a dedicated `backups` directory to keep the root directory clean.

2. **Automatic Redaction**: Sensitive information in configuration files (like `wrangler.toml`, `.env`, etc.) is automatically redacted before backup. This includes:

   - Cloudflare Account ID
   - Cloudflare Access Key ID
   - Cloudflare Secret Access Key
   - JWT Secret
   - Admin Password

3. **Timestamped Backups**: Each backup is stored in a timestamped directory for easy identification.

4. **Backup Management**: The system can automatically manage old backups, keeping only the most recent ones to save disk space.

### Help Command

To see all available commands and their options:

```bash
bricks-deal help
```

To get help for a specific command:

```bash
bricks-deal [command] --help
```
