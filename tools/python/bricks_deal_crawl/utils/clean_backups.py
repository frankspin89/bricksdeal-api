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

def clean_old_backups(backup_dir="backups", max_backups=5, dry_run=False, force=False):
    """Clean old backups, keeping only the most recent ones."""
    print_header("Backup Cleanup Utility")
    print(f"{Colors.CYAN}This tool will clean up old backups, keeping only the most recent ones.{Colors.ENDC}")
    print(f"{Colors.CYAN}Options:{Colors.ENDC}")
    print(f"{Colors.CYAN}- Max backups: {max_backups}{Colors.ENDC}")
    if dry_run:
        print(f"{Colors.CYAN}- Dry run: Backups will not be actually deleted{Colors.ENDC}")
    print()
    
    if not os.path.exists(backup_dir):
        print_warning(f"Backup directory {backup_dir} does not exist. Nothing to clean.")
        return 0
    
    # Get all backup directories
    backup_dirs = []
    for item in os.listdir(backup_dir):
        item_path = os.path.join(backup_dir, item)
        if os.path.isdir(item_path) and (item.startswith("backup_") or item.startswith("cloudflare_backup_")):
            backup_dirs.append(item_path)
    
    if not backup_dirs:
        print_warning(f"No backup directories found in {backup_dir}. Nothing to clean.")
        return 0
    
    # Sort by modification time (newest first)
    backup_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print_step(f"Found {len(backup_dirs)} backup directories")
    
    # Remove old backups
    if len(backup_dirs) > max_backups:
        old_backups = backup_dirs[max_backups:]
        print_step(f"Found {len(old_backups)} old backups to clean up")
        
        # Confirm action if not forced or dry run
        if not force and not dry_run:
            if not confirm_action(f"Are you sure you want to delete {len(old_backups)} old backup directories?"):
                print_warning("Operation cancelled by user.")
                return 0
        
        for old_backup in old_backups:
            if dry_run:
                print_step(f"Would remove old backup: {old_backup}")
            else:
                try:
                    shutil.rmtree(old_backup)
                    print_success(f"Removed old backup: {old_backup}")
                except Exception as e:
                    print_error(f"Error removing old backup {old_backup}: {str(e)}")
        
        if not dry_run:
            print_success(f"Removed {len(old_backups)} old backup directories")
    else:
        print_success(f"You have {len(backup_dirs)} backups, which is less than or equal to the maximum of {max_backups}. Nothing to clean.")
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="Clean old backups")
    parser.add_argument("--max-backups", type=int, default=5, help="Maximum number of backups to keep (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    parser.add_argument("--backup-dir", type=str, default="backups", help="Backup directory (default: backups)")
    
    args = parser.parse_args()
    
    return clean_old_backups(
        backup_dir=args.backup_dir,
        max_backups=args.max_backups,
        dry_run=args.dry_run,
        force=args.force
    )

if __name__ == "__main__":
    sys.exit(main()) 