#!/usr/bin/env python3

import os
import shutil
import argparse
import glob
from datetime import datetime
import sys
import re

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}\n")

def print_step(message):
    """Print a formatted step message."""
    print(f"{Colors.BLUE}→ {message}{Colors.ENDC}")

def print_success(message):
    """Print a formatted success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a formatted warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_error(message):
    """Print a formatted error message."""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")

def confirm_action(message):
    """Ask the user to confirm an action."""
    response = input(f"{Colors.WARNING}{Colors.BOLD}? {message} (y/N): {Colors.ENDC}").lower()
    return response == 'y'

def ensure_directory(directory):
    """Ensure a directory exists."""
    os.makedirs(directory, exist_ok=True)
    print_step(f"Created directory: {directory}")

def sanitize_file(source_path, dest_path):
    """Sanitize a file by removing sensitive information."""
    # Patterns to match sensitive information
    patterns = [
        # wrangler.toml format
        (r'CLOUDFLARE_ACCOUNT_ID\s*=\s*"[^"]*"', 'CLOUDFLARE_ACCOUNT_ID = "***REDACTED***"'),
        (r'CLOUDFLARE_ACCESS_KEY_ID\s*=\s*"[^"]*"', 'CLOUDFLARE_ACCESS_KEY_ID = "***REDACTED***"'),
        (r'CLOUDFLARE_SECRET_ACCESS_KEY\s*=\s*"[^"]*"', 'CLOUDFLARE_SECRET_ACCESS_KEY = "***REDACTED***"'),
        (r'JWT_SECRET\s*=\s*"[^"]*"', 'JWT_SECRET = "***REDACTED***"'),
        (r'ADMIN_PASSWORD\s*=\s*"[^"]*"', 'ADMIN_PASSWORD = "***REDACTED***"'),
        
        # .env format
        (r'CLOUDFLARE_ACCOUNT_ID=.*', 'CLOUDFLARE_ACCOUNT_ID=***REDACTED***'),
        (r'CLOUDFLARE_ACCESS_KEY_ID=.*', 'CLOUDFLARE_ACCESS_KEY_ID=***REDACTED***'),
        (r'CLOUDFLARE_SECRET_ACCESS_KEY=.*', 'CLOUDFLARE_SECRET_ACCESS_KEY=***REDACTED***'),
        (r'JWT_SECRET=.*', 'JWT_SECRET=***REDACTED***'),
        (r'ADMIN_PASSWORD=.*', 'ADMIN_PASSWORD=***REDACTED***'),
        (r'DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=***REDACTED***'),
        (r'OXYLABS_USERNAME=.*', 'OXYLABS_USERNAME=***REDACTED***'),
        (r'OXYLABS_PASSWORD=.*', 'OXYLABS_PASSWORD=***REDACTED***'),
        
        # Generic API keys and tokens
        (r'(api[_-]?key|apikey|token|secret|password|credential)s?\s*[=:]\s*["\'`]?[a-zA-Z0-9_\-\.]{20,}["\'`]?', r'\1=***REDACTED***'),
        (r'(sk|pk|api|token|key)-[a-zA-Z0-9]{20,}', '***REDACTED***'),
    ]
    
    try:
        with open(source_path, 'r') as f:
            content = f.read()
        
        # Apply all patterns
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        with open(dest_path, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print_error(f"Error sanitizing file {source_path}: {str(e)}")
        return False

def backup_files(files, backup_dir):
    """Backup files to a specified directory."""
    backed_up_files = 0
    for file_path in files:
        if os.path.exists(file_path):
            # Create the destination path
            filename = os.path.basename(file_path)
            dest_path = os.path.join(backup_dir, filename)
            
            # Check if the file might contain sensitive information
            if filename.lower() in ['wrangler.toml', '.env', 'config.json', 'secrets.json']:
                print_step(f"Sanitizing sensitive file: {file_path}")
                if sanitize_file(file_path, dest_path):
                    print_success(f"Backed up sanitized version of {file_path} to {dest_path}")
                    backed_up_files += 1
            else:
                # Copy the file
                shutil.copy2(file_path, dest_path)
                print_success(f"Backed up {file_path} to {dest_path}")
                backed_up_files += 1
        else:
            print_warning(f"File {file_path} does not exist. Skipping backup.")
    
    return backed_up_files

def remove_directory(directory, dry_run=False):
    """Remove a directory and all its contents."""
    if not os.path.exists(directory):
        print_warning(f"Directory {directory} does not exist. Skipping.")
        return
    
    if dry_run:
        file_count = sum(len(files) for _, _, files in os.walk(directory))
        print_step(f"Would remove directory: {directory} (contains {file_count} files)")
        return
    
    # Remove the directory
    shutil.rmtree(directory)
    print_success(f"Removed directory: {directory}")

def remove_files(file_patterns, dry_run=False):
    """Remove files matching the given patterns."""
    total_removed = 0
    
    for pattern in file_patterns:
        matching_files = glob.glob(pattern)
        
        if not matching_files:
            print_warning(f"No files match pattern: {pattern}. Skipping.")
            continue
        
        if dry_run:
            print_step(f"Would remove {len(matching_files)} files matching pattern: {pattern}")
            continue
        
        # Remove the files
        for file_path in matching_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                total_removed += 1
                
                # Print progress for large file sets
                if len(matching_files) > 10 and total_removed % 10 == 0:
                    progress = (total_removed / len(matching_files)) * 100
                    print(f"\rRemoving files... {progress:.1f}% ({total_removed}/{len(matching_files)})", end="")
                    sys.stdout.flush()
        
        if len(matching_files) > 10:
            print()  # New line after progress indicator
            
        print_success(f"Removed {len(matching_files)} files matching pattern: {pattern}")
    
    return total_removed

def clean_old_backups(backup_dir, max_backups=5, dry_run=False):
    """Clean old backups, keeping only the most recent ones."""
    if not os.path.exists(backup_dir):
        print_warning(f"Backup directory {backup_dir} does not exist. Skipping cleanup.")
        return
    
    # Get all backup directories
    backup_dirs = []
    for item in os.listdir(backup_dir):
        item_path = os.path.join(backup_dir, item)
        if os.path.isdir(item_path) and item.startswith("backup_"):
            backup_dirs.append(item_path)
    
    # Sort by modification time (newest first)
    backup_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Remove old backups
    if len(backup_dirs) > max_backups:
        old_backups = backup_dirs[max_backups:]
        print_step(f"Found {len(old_backups)} old backups to clean up")
        
        for old_backup in old_backups:
            if dry_run:
                print_step(f"Would remove old backup: {old_backup}")
            else:
                shutil.rmtree(old_backup)
                print_success(f"Removed old backup: {old_backup}")

def main(args=None):
    """Clean up temporary files and directories."""
    if args is None:
        parser = argparse.ArgumentParser(description="Clean up temporary files and directories")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
        parser.add_argument("--backup", action="store_true", help="Backup files before removing them")
        parser.add_argument("--deep-clean", action="store_true", help="Perform a deeper cleanup, removing temporary files")
        parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
        parser.add_argument("--max-backups", type=int, default=5, help="Maximum number of backups to keep")
        
        args = parser.parse_args()
    
    # Set default values if not present in args
    dry_run = getattr(args, 'dry_run', False)
    backup = getattr(args, 'backup', False)
    deep_clean = getattr(args, 'deep_clean', False)
    force = getattr(args, 'force', False)
    max_backups = getattr(args, 'max_backups', 5)
    
    # Print welcome message
    print_header("Bricks Deal Cleanup Utility")
    print(f"{Colors.CYAN}This tool will clean up temporary files and directories in the Bricks Deal project.{Colors.ENDC}")
    print(f"{Colors.CYAN}Options:{Colors.ENDC}")
    if dry_run:
        print(f"{Colors.CYAN}- Dry run: Files will not be actually deleted{Colors.ENDC}")
    if backup:
        print(f"{Colors.CYAN}- Backup: Important files will be backed up before cleaning{Colors.ENDC}")
    if deep_clean:
        print(f"{Colors.CYAN}- Deep clean: Additional temporary files will be removed{Colors.ENDC}")
    print()
    
    # Confirm action if not forced or dry run
    if not force and not dry_run:
        if not confirm_action("Are you sure you want to clean up temporary files and directories?"):
            print_warning("Operation cancelled by user.")
            return 0
    
    # Create a backup directory if needed
    backup_dir = None
    backed_up_files = 0
    if backup:
        # Create the main backups directory if it doesn't exist
        main_backup_dir = "backups"
        ensure_directory(main_backup_dir)
        
        # Create a timestamped subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(main_backup_dir, f"backup_{timestamp}")
        ensure_directory(backup_dir)
        
        # Backup important files
        print_header("Backing up important files")
        important_files = [
            "schema.sql",
            "apps/api/wrangler.toml",
            ".env"
        ]
        
        backed_up_files = backup_files(important_files, backup_dir)
        
        # Clean old backups
        clean_old_backups(main_backup_dir, max_backups, dry_run)
    
    # Clean old backup directories in the root (from previous versions)
    old_backup_patterns = ["backup_*"]
    for pattern in old_backup_patterns:
        old_backups = glob.glob(pattern)
        if old_backups:
            print_header(f"Cleaning old backup directories in root")
            for old_backup in old_backups:
                if os.path.isdir(old_backup):
                    if dry_run:
                        print_step(f"Would move old backup directory: {old_backup} to backups/")
                    else:
                        # Move to the new backups directory
                        try:
                            dest_path = os.path.join("backups", os.path.basename(old_backup))
                            shutil.move(old_backup, dest_path)
                            print_success(f"Moved old backup directory: {old_backup} to backups/")
                        except Exception as e:
                            print_error(f"Error moving old backup directory: {str(e)}")
    
    # Directories to clean
    print_header("Cleaning directories")
    directories_to_clean = [
        "tmp",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build"
    ]
    
    for directory in directories_to_clean:
        remove_directory(directory, dry_run)
    
    # Remove temporary files
    print_header("Cleaning temporary files")
    temp_file_patterns = [
        "*.log",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.c",
        "*.h",
        "*.o",
        "*.obj",
        "*.dll",
        "*.exe",
        "*.egg-info",
        "*.egg",
        "*.whl",
        "*.coverage",
        "*.cache",
        "*.DS_Store"
    ]
    
    # If deep clean is requested, add more patterns
    if deep_clean:
        print_header("Deep cleaning additional files")
        deep_clean_patterns = [
            "raw_lego_product_*.json",
            "price_history_*.json",
            "processed_lego_*.json",
            "d1_*.sql"
        ]
        temp_file_patterns.extend(deep_clean_patterns)
    
    total_removed = remove_files(temp_file_patterns, dry_run)
    
    # Print summary
    print_header("Cleanup Summary")
    
    if dry_run:
        print_success("Dry run completed. No files were actually removed.")
    else:
        print_success(f"Cleanup completed. Removed {total_removed} files.")
    
    if backup:
        if backed_up_files > 0:
            print_success(f"Backed up {backed_up_files} important files to the {backup_dir} directory.")
            print_success(f"Note: Sensitive information has been redacted from configuration files.")
        else:
            print_warning("No files were backed up as none of the specified files exist.")
            # Remove the empty backup directory
            if os.path.exists(backup_dir) and not os.listdir(backup_dir):
                os.rmdir(backup_dir)
                print_step(f"Removed empty backup directory: {backup_dir}")
    
    if deep_clean:
        print_success("Deep clean completed. Additional temporary files were removed.")
    
    return 0

if __name__ == "__main__":
    main() 