"""
Catalog Module

This module handles LEGO catalog data extraction, processing, and management.

Components:
----------
- extract: Extract LEGO catalog data from Rebrickable
- process: Process and transform LEGO catalog data
- image_processor: Process and optimize LEGO catalog images

Main Functions:
-------------
- extract_catalog_data: Extract LEGO catalog data from Rebrickable
- process_image_urls: Process image URLs to create SEO-friendly URLs
- update_csv_with_image_urls: Update CSV files with processed image URLs

Features:
--------
- SEO-friendly image URL generation
- CSV data extraction and processing
- Image optimization and transformation
- Catalog data enrichment

Usage:
-----
To extract catalog data:
    bricks-deal extract-catalog

To process images with SEO-friendly URLs:
    bricks-deal extract-catalog --process-images

To update CSV files with new image URLs:
    bricks-deal extract-catalog --update-csv
"""
