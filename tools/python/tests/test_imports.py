#!/usr/bin/env python3
"""
Test that all modules can be imported correctly.
"""

import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported."""

    def test_main_import(self):
        """Test that the main module can be imported."""
        from bricks_deal_crawl import main
        self.assertIsNotNone(main)

    def test_catalog_import(self):
        """Test that the catalog module can be imported."""
        from bricks_deal_crawl.catalog import extract
        self.assertIsNotNone(extract)

    def test_utils_import(self):
        """Test that the utils module can be imported."""
        from bricks_deal_crawl.utils import update_prices
        self.assertIsNotNone(update_prices)

    def test_scrapers_import(self):
        """Test that the scrapers module can be imported."""
        from bricks_deal_crawl.scrapers import lego_direct
        self.assertIsNotNone(lego_direct)

    def test_database_import(self):
        """Test that the database module can be imported."""
        from bricks_deal_crawl.database import setup
        self.assertIsNotNone(setup)

    def test_export_import(self):
        """Test that the export module can be imported."""
        from bricks_deal_crawl.export import cloudflare
        self.assertIsNotNone(cloudflare)


if __name__ == '__main__':
    unittest.main() 