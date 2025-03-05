"""
Bricks Deal Crawl - Main Module

This is the main entry point for the Bricks Deal Crawl package, providing a command-line interface
for all functionality related to LEGO catalog data extraction, processing, and management.

Components:
----------
- Command-line interface for all package functionality
- Argument parsing and command routing
- Logging configuration

Main Commands:
-------------
- extract-catalog: Extract and process LEGO catalog data
- update-prices: Update prices for LEGO products
- setup-database: Set up the LEGO catalog database
- export: Export LEGO catalog data to various targets

Usage:
-----
To run the main CLI:
    bricks-deal [command] [options]

Examples:
    bricks-deal extract-catalog --process-images
    bricks-deal update-prices --set-num 10423-1
    bricks-deal setup-database
    bricks-deal export --target cloudflare
""" 