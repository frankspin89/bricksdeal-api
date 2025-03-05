# Bricks Deal Python Tools

This directory contains the Python tools for the Bricks Deal project, including:

- LEGO catalog data extraction and processing
- Database setup and management
- Price updates and tracking
- Export functionality for Cloudflare R2 and D1

## Installation

```bash
# From the tools/python directory
pip install -e .
```

## Usage

```bash
# Extract catalog data
bricks-deal extract-catalog

# Process images with SEO-friendly URLs
bricks-deal extract-catalog --process-images

# Update prices
bricks-deal update-prices

# Setup database
bricks-deal setup-db

# Export to Cloudflare
bricks-deal export --target cloudflare
```

For more detailed documentation, see the main [README.md](../../README.md) and [WORKFLOW.md](../../WORKFLOW.md) files. 