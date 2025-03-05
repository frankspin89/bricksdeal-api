#!/usr/bin/env python3
"""
Utility script to update imports in the moved files to be compatible with the new package structure.
"""

import os
import re
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def update_imports_in_file(file_path):
    """Update imports in a file to be compatible with the new package structure."""
    print(f"Updating imports in {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update relative imports to use the new package structure
    # For example, "import extract_catalog_data" -> "from bricks_deal_crawl.catalog import extract"
    
    # Map of old import to new import
    import_map = {
        # Main scripts
        r'import\s+extract_catalog_data': 'from bricks_deal_crawl.catalog import extract',
        r'from\s+extract_catalog_data\s+import': 'from bricks_deal_crawl.catalog.extract import',
        r'import\s+extract_lego_data': 'from bricks_deal_crawl.catalog import lego_data',
        r'from\s+extract_lego_data\s+import': 'from bricks_deal_crawl.catalog.lego_data import',
        
        r'import\s+setup_database': 'from bricks_deal_crawl.database import setup',
        r'from\s+setup_database\s+import': 'from bricks_deal_crawl.database.setup import',
        r'import\s+create_clean_db': 'from bricks_deal_crawl.database import clean',
        r'from\s+create_clean_db\s+import': 'from bricks_deal_crawl.database.clean import',
        r'import\s+enrich_database': 'from bricks_deal_crawl.database import enrich',
        r'from\s+enrich_database\s+import': 'from bricks_deal_crawl.database.enrich import',
        
        r'import\s+export_to_cloudflare': 'from bricks_deal_crawl.export import cloudflare',
        r'from\s+export_to_cloudflare\s+import': 'from bricks_deal_crawl.export.cloudflare import',
        r'import\s+export_to_d1': 'from bricks_deal_crawl.export import d1',
        r'from\s+export_to_d1\s+import': 'from bricks_deal_crawl.export.d1 import',
        r'import\s+update_d1_directly': 'from bricks_deal_crawl.export import update_d1',
        r'from\s+update_d1_directly\s+import': 'from bricks_deal_crawl.export.update_d1 import',
        
        r'import\s+scrape_lego_direct': 'from bricks_deal_crawl.scrapers import lego_direct',
        r'from\s+scrape_lego_direct\s+import': 'from bricks_deal_crawl.scrapers.lego_direct import',
        r'import\s+scrape_new_products': 'from bricks_deal_crawl.scrapers import new_products',
        r'from\s+scrape_new_products\s+import': 'from bricks_deal_crawl.scrapers.new_products import',
        
        r'import\s+cleanup': 'from bricks_deal_crawl.utils import cleanup',
        r'from\s+cleanup\s+import': 'from bricks_deal_crawl.utils.cleanup import',
        r'import\s+update_prices': 'from bricks_deal_crawl.utils import update_prices',
        r'from\s+update_prices\s+import': 'from bricks_deal_crawl.utils.update_prices import',
        r'import\s+update_processed_urls': 'from bricks_deal_crawl.utils import update_processed_urls',
        r'from\s+update_processed_urls\s+import': 'from bricks_deal_crawl.utils.update_processed_urls import',
        
        # Workflow script
        r'import\s+lego_scraper_workflow': 'from bricks_deal_crawl import main',
        r'from\s+lego_scraper_workflow\s+import': 'from bricks_deal_crawl.main import',
        
        # Also update any remaining src references
        r'from\s+src\.': 'from bricks_deal_crawl.',
        r'import\s+src\.': 'import bricks_deal_crawl.',
    }
    
    # Apply the import replacements
    for old_import, new_import in import_map.items():
        content = re.sub(old_import, new_import, content)
    
    # Update file paths to use the new package structure
    # For example, "os.path.join('input', 'lego-catalog')" remains the same
    # since we're keeping the input/output directories as they were
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated imports in {file_path}")


def update_imports_in_directory(directory):
    """Update imports in all Python files in a directory and its subdirectories."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                update_imports_in_file(file_path)


def main():
    """Main entry point for the script."""
    # Update imports in the src directory
    update_imports_in_directory('src')
    
    print("Done updating imports!")


if __name__ == "__main__":
    main() 