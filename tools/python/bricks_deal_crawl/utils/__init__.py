"""
Utils Module

This module provides utility functions for various tasks in the Bricks Deal Crawl package.

Components:
----------
- update_prices: Update prices for LEGO products
- cleanup: Clean up temporary files and directories
- update_processed_urls: Update the list of processed URLs
- clean: Clean Cloudflare R2 bucket and D1 database

Main Functions:
-------------
- update_all_prices: Update prices for all LEGO products
- check_product_price: Check the price of a specific LEGO product
- generate_price_change_report: Generate a report of price changes
- clean_r2_bucket: Clean the Cloudflare R2 bucket
- clean_d1_database: Clean the Cloudflare D1 database

Usage:
-----
To update prices for all products:
    bricks-deal update-prices

To update price for a specific set:
    bricks-deal update-prices --set-num 10423-1
    
To clean Cloudflare resources:
    bricks-deal clean --r2  # Clean R2 bucket
    bricks-deal clean --d1  # Clean D1 database
    bricks-deal clean       # Clean both
"""

