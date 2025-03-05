#!/usr/bin/env python3
"""
Utility script to clean up old files that have been moved to the package structure.
"""

import os
import sys
import shutil
from pathlib import Path

# List of old files that have been moved to the package structure
OLD_FILES = [
    "extract_catalog_data.py",
    "extract_lego_data.py",
    "setup_database.py",
    "create_clean_db.py",
    "enrich_database.py",
    "export_to_cloudflare.py",
    "export_to_d1.py",
    "update_d1_directly.py",
    "scrape_lego_direct.py",
    "scrape_new_products.py",
    "cleanup.py",
    "update_prices.py",
    "update_processed_urls.py",
    "lego_scraper_workflow.py",
]

# Additional files to clean up
ADDITIONAL_FILES = [
    "results.json",
    "scrape_summary.json",
]

# Files in the src directory to clean up
SRC_FILES = [
    "src/main.py",
    "src/__init__.py",
    "src/index.js",
]

# Directories to clean up
DIRS_TO_CLEAN = [
    "__pycache__",
    "tmp",
    "src/__pycache__",
]

# Directory to move old files to
BACKUP_DIR = "old_files_backup"


def backup_old_files():
    """Backup old files to a backup directory."""
    # Create backup directory if it doesn't exist
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created backup directory: {BACKUP_DIR}")
    
    # Create src directory in backup directory if it doesn't exist
    src_backup_dir = os.path.join(BACKUP_DIR, "src")
    if not os.path.exists(src_backup_dir):
        os.makedirs(src_backup_dir)
        print(f"Created src backup directory: {src_backup_dir}")
    
    # Move old files to backup directory
    for file in OLD_FILES + ADDITIONAL_FILES:
        if os.path.exists(file):
            backup_path = os.path.join(BACKUP_DIR, file)
            shutil.move(file, backup_path)
            print(f"Moved {file} to {backup_path}")
        else:
            print(f"File not found: {file}")
    
    # Move src files to backup directory
    for file in SRC_FILES:
        if os.path.exists(file):
            # Get the filename without the path
            filename = os.path.basename(file)
            backup_path = os.path.join(src_backup_dir, filename)
            shutil.move(file, backup_path)
            print(f"Moved {file} to {backup_path}")
        else:
            print(f"File not found: {file}")
    
    # Move directories to backup directory
    for dir_name in DIRS_TO_CLEAN:
        if os.path.exists(dir_name):
            # If the directory is in the src directory, move it to the src backup directory
            if dir_name.startswith("src/"):
                # Get the directory name without the path
                dirname = os.path.basename(dir_name)
                backup_path = os.path.join(src_backup_dir, dirname)
            else:
                backup_path = os.path.join(BACKUP_DIR, dir_name)
            
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.move(dir_name, backup_path)
            print(f"Moved {dir_name} to {backup_path}")
        else:
            print(f"Directory not found: {dir_name}")


def delete_old_files():
    """Delete old files that have been moved to the package structure."""
    for file in OLD_FILES + ADDITIONAL_FILES:
        if os.path.exists(file):
            os.remove(file)
            print(f"Deleted {file}")
        else:
            print(f"File not found: {file}")
    
    # Delete src files
    for file in SRC_FILES:
        if os.path.exists(file):
            os.remove(file)
            print(f"Deleted {file}")
        else:
            print(f"File not found: {file}")
    
    # Delete directories
    for dir_name in DIRS_TO_CLEAN:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Deleted directory: {dir_name}")
        else:
            print(f"Directory not found: {dir_name}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        delete_old_files()
    else:
        backup_old_files()
    
    print("Done cleaning up old files!")


if __name__ == "__main__":
    main() 