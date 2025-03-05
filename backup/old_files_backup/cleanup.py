#!/usr/bin/env python3

import os
import shutil
import argparse
import glob
from datetime import datetime

def ensure_directory(directory):
    """Ensure a directory exists."""
    os.makedirs(directory, exist_ok=True)

def backup_files(files, backup_dir):
    """Backup files to a specified directory."""
    for file_path in files:
        if os.path.exists(file_path):
            # Create the destination path
            filename = os.path.basename(file_path)
            dest_path = os.path.join(backup_dir, filename)
            
            # Copy the file
            shutil.copy2(file_path, dest_path)
            print(f"Backed up {file_path} to {dest_path}")

def remove_directory(directory, dry_run=False):
    """Remove a directory and all its contents."""
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist. Skipping.")
        return
    
    if dry_run:
        print(f"Would remove directory: {directory}")
        print(f"Contains {sum(len(files) for _, _, files in os.walk(directory))} files")
        return
    
    # Remove the directory
    shutil.rmtree(directory)
    print(f"Removed directory: {directory}")

def remove_files(file_patterns, dry_run=False):
    """Remove files matching the given patterns."""
    for pattern in file_patterns:
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            print(f"No files match pattern: {pattern}. Skipping.")
            continue
        
        if dry_run:
            print(f"Would remove {len(matching_files)} files matching pattern: {pattern}")
            continue
        
        # Remove the files
        for file_path in matching_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed file: {file_path}")
        
        print(f"Removed {len(matching_files)} files matching pattern: {pattern}")

def create_readme_update():
    """Create an update for the README file."""
    readme_update = """
# LEGO Database Workflow

## Initial Setup

1. Create a clean SQLite database:
   ```bash
   python3 create_clean_db.py --force
   ```

2. Import LEGO catalog data:
   ```bash
   python3 import_lego_catalog.py
   ```

3. Export to Cloudflare D1 (one-time setup):
   ```bash
   # Backup the export scripts if needed
   python3 cleanup.py --backup
   
   # Create and deploy the D1 database
   wrangler d1 create bricksdeal
   wrangler d1 execute bricksdeal --file schema.sql --remote
   ```

## Regular Updates

1. Scrape LEGO product data:
   ```bash
   python3 lego_scraper_workflow.py --product-id 10353
   ```

2. Optimize images (optional):
   ```bash
   python3 lego_scraper_workflow.py --optimize-images 10353
   ```

3. Update Cloudflare D1 directly:
   ```bash
   python3 update_d1_directly.py --product-id 10353
   ```

4. Deploy Worker (when needed):
   ```bash
   wrangler deploy
   ```

## Cleanup

If you need to clean up the codebase:
```bash
python3 cleanup.py
```

This will remove the `d1_export` folder and other temporary files.
"""
    
    # Write to a file
    with open("WORKFLOW.md", "w") as f:
        f.write(readme_update)
    
    print("Created WORKFLOW.md with updated workflow documentation")

def main():
    parser = argparse.ArgumentParser(description="Clean up the codebase")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--backup", action="store_true", help="Backup export scripts before removing them")
    parser.add_argument("--deep-clean", action="store_true", help="Perform a deeper cleanup, removing temporary files")
    
    args = parser.parse_args()
    
    # Create a backup directory if needed
    backup_dir = None
    if args.backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup_{timestamp}"
        ensure_directory(backup_dir)
        print(f"Created backup directory: {backup_dir}")
        
        # Backup export scripts
        export_scripts = [
            "export_to_cloudflare.py",
            "export_to_d1.py"
        ]
        
        backup_files(export_scripts, backup_dir)
        
        # Extract schema.sql from d1_export if it exists
        schema_path = os.path.join("d1_export", "schema.sql")
        if os.path.exists(schema_path):
            shutil.copy2(schema_path, "schema.sql")
            print(f"Extracted schema.sql from d1_export")
    
    # Remove d1_export directory
    remove_directory("d1_export", args.dry_run)
    
    # Remove temporary files if deep clean is requested
    if args.deep_clean:
        temp_file_patterns = [
            "raw_lego_product_*.json",
            "price_history_*.json",
            "processed_lego_*.json",
            "d1_*.sql",
            "tmp/*",
            "*.log",
            "__pycache__/*.pyc"
        ]
        
        remove_files(temp_file_patterns, args.dry_run)
    
    # Create README update
    create_readme_update()
    
    print("\nCleanup complete!")
    print("The d1_export folder has been removed, and a new WORKFLOW.md file has been created.")
    print("Please review the WORKFLOW.md file for the updated workflow.")
    
    if args.backup:
        print(f"\nExport scripts have been backed up to the {backup_dir} directory.")
        print("If you need to use them again, you can find them there.")
    
    if args.deep_clean:
        print("\nDeep clean completed. Temporary files have been removed.")
        print("This should improve your IDE performance.")

if __name__ == "__main__":
    main() 