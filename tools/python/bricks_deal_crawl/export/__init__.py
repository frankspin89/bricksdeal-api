"""
Export Module

This module provides functionality for exporting LEGO catalog data to various targets.

Components:
----------
- cloudflare: Export data to Cloudflare R2 and D1
- d1: Export data to Cloudflare D1
- update_d1: Update Cloudflare D1 directly

Main Functions:
-------------
- export_to_cloudflare: Export data to Cloudflare R2 and D1
- export_to_d1: Export data to Cloudflare D1
- update_d1_directly: Update Cloudflare D1 directly

Usage:
-----
To export data to Cloudflare:
    bricks-deal export --target cloudflare

To export data to D1:
    bricks-deal export --target d1
"""

