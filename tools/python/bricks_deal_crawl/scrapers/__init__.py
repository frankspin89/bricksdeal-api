"""
Scrapers Module

This module provides functionality for scraping LEGO product data from various sources.

Components:
----------
- lego_direct: Scrape LEGO product data from LEGO's website
- new_products: Scrape new LEGO product URLs from LEGO's website

Main Functions:
-------------
- fetch_lego_product: Fetch LEGO product data from LEGO's website
- scrape_new_products: Scrape new LEGO product URLs from LEGO's website
- ProxyManager: Manage proxies for scraping

Features:
--------
- Proxy rotation to avoid IP blocks
- Parallel processing for efficiency
- Error handling and retries
- Detailed logging
"""

