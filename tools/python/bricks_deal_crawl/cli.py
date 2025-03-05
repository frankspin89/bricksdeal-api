#!/usr/bin/env python3

import argparse
import sys
from bricks_deal_crawl.utils.extract_catalog import main as extract_catalog_main
from bricks_deal_crawl.utils.update_prices import main as update_prices_main
from bricks_deal_crawl.utils.setup_db import main as setup_db_main
from bricks_deal_crawl.utils.export import main as export_main
from bricks_deal_crawl.utils.clean import main as clean_main
from bricks_deal_crawl.utils.cleanup import main as cleanup_main
from bricks_deal_crawl.utils.clean_backups import clean_old_backups

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

def print_logo():
    """Print the Bricks Deal logo."""
    logo = f"""
{Colors.CYAN}{Colors.BOLD}
 ____       _      _          ____            _ 
| __ ) _ __(_) ___| | _____  |  _ \  ___  ___| |
|  _ \| '__| |/ __| |/ / __| | | | |/ _ \/ _ \ |
| |_) | |  | | (__|   <\__ \ | |_| |  __/  __/ |
|____/|_|  |_|\___|_|\_\___/ |____/ \___|\___|_|
{Colors.ENDC}
{Colors.BLUE}Lego Price Tracking and Analysis Tool{Colors.ENDC}
"""
    print(logo)

def print_command_help(command, description, usage=None, options=None):
    """Print help for a specific command."""
    print(f"{Colors.BOLD}{Colors.BLUE}Command:{Colors.ENDC} {Colors.CYAN}{command}{Colors.ENDC}")
    print(f"{Colors.BOLD}Description:{Colors.ENDC} {description}")
    
    if usage:
        print(f"{Colors.BOLD}Usage:{Colors.ENDC} {usage}")
    
    if options:
        print(f"{Colors.BOLD}Options:{Colors.ENDC}")
        for option, desc in options:
            print(f"  {Colors.CYAN}{option}{Colors.ENDC} - {desc}")
    
    print()

def show_help():
    """Show detailed help information."""
    print_logo()
    print(f"{Colors.BOLD}{Colors.HEADER}Available Commands:{Colors.ENDC}\n")
    
    print_command_help(
        "extract-catalog", 
        "Extract catalog data from Brickset API and store it in the database.",
        "bricks-deal extract-catalog [--year YEAR] [--theme THEME]",
        [
            ("--year YEAR", "Extract data for a specific year"),
            ("--theme THEME", "Extract data for a specific theme")
        ]
    )
    
    print_command_help(
        "update-prices", 
        "Update prices from BrickLink for sets in the database.",
        "bricks-deal update-prices [--limit LIMIT] [--offset OFFSET]",
        [
            ("--limit LIMIT", "Limit the number of sets to update"),
            ("--offset OFFSET", "Start updating from this offset")
        ]
    )
    
    print_command_help(
        "setup-db", 
        "Set up the database schema.",
        "bricks-deal setup-db [--local] [--remote]",
        [
            ("--local", "Set up the local database"),
            ("--remote", "Set up the remote database")
        ]
    )
    
    print_command_help(
        "export", 
        "Export data from the database to CSV files.",
        "bricks-deal export [--sets] [--prices] [--themes]",
        [
            ("--sets", "Export sets data"),
            ("--prices", "Export prices data"),
            ("--themes", "Export themes data")
        ]
    )
    
    print_command_help(
        "clean", 
        "Clean Cloudflare resources (R2 bucket and D1 database).",
        "bricks-deal clean [--r2] [--d1] [--force] [--backup]",
        [
            ("--r2", "Clean only the R2 bucket"),
            ("--d1", "Clean only the D1 database"),
            ("--force", "Force cleaning without confirmation"),
            ("--backup", "Create a backup before cleaning")
        ]
    )
    
    print_command_help(
        "cleanup", 
        "Clean up temporary files and directories.",
        "bricks-deal cleanup [--force] [--dry-run] [--deep-clean] [--backup]",
        [
            ("--force", "Force cleanup without confirmation"),
            ("--dry-run", "Show what would be deleted without actually deleting"),
            ("--deep-clean", "Perform a deep clean (including node_modules)"),
            ("--backup", "Create a backup before cleaning")
        ]
    )
    
    print_command_help(
        "clean-backups", 
        "Clean old backup directories, keeping only the most recent ones.",
        "bricks-deal clean-backups [--max-backups NUM] [--dry-run] [--force]",
        [
            ("--max-backups NUM", "Maximum number of backups to keep (default: 5)"),
            ("--dry-run", "Show what would be deleted without actually deleting"),
            ("--force", "Force cleaning without confirmation"),
            ("--backup-dir DIR", "Backup directory (default: backups)")
        ]
    )
    
    print_command_help(
        "help", 
        "Show this help message.",
        "bricks-deal help"
    )
    
    print(f"{Colors.BOLD}{Colors.HEADER}Common Workflows:{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Initial Setup:{Colors.ENDC}")
    print(f"  1. {Colors.CYAN}bricks-deal setup-db --local --remote{Colors.ENDC}")
    print(f"  2. {Colors.CYAN}bricks-deal extract-catalog{Colors.ENDC}")
    print(f"  3. {Colors.CYAN}bricks-deal update-prices{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Regular Updates:{Colors.ENDC}")
    print(f"  1. {Colors.CYAN}bricks-deal extract-catalog --year 2023{Colors.ENDC}")
    print(f"  2. {Colors.CYAN}bricks-deal update-prices{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Maintenance:{Colors.ENDC}")
    print(f"  - {Colors.CYAN}bricks-deal cleanup{Colors.ENDC} (clean temporary files)")
    print(f"  - {Colors.CYAN}bricks-deal clean{Colors.ENDC} (clean Cloudflare resources)")
    print(f"  - {Colors.CYAN}bricks-deal export{Colors.ENDC} (export data for analysis)\n")
    
    print(f"{Colors.BOLD}{Colors.HEADER}For more information on a specific command:{Colors.ENDC}")
    print(f"  {Colors.CYAN}bricks-deal [command] --help{Colors.ENDC}\n")

def main():
    parser = argparse.ArgumentParser(description="Bricks Deal CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract catalog command
    extract_parser = subparsers.add_parser("extract-catalog", help="Extract catalog data from Brickset API")
    extract_parser.add_argument("--year", type=int, help="Extract data for a specific year")
    extract_parser.add_argument("--theme", type=str, help="Extract data for a specific theme")
    
    # Update prices command
    update_parser = subparsers.add_parser("update-prices", help="Update prices from BrickLink")
    update_parser.add_argument("--limit", type=int, help="Limit the number of sets to update")
    update_parser.add_argument("--offset", type=int, help="Start updating from this offset")
    
    # Setup database command
    setup_parser = subparsers.add_parser("setup-db", help="Set up the database schema")
    setup_parser.add_argument("--local", action="store_true", help="Set up the local database")
    setup_parser.add_argument("--remote", action="store_true", help="Set up the remote database")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data from the database")
    export_parser.add_argument("--sets", action="store_true", help="Export sets data")
    export_parser.add_argument("--prices", action="store_true", help="Export prices data")
    export_parser.add_argument("--themes", action="store_true", help="Export themes data")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean Cloudflare resources (R2 bucket and D1 database)")
    clean_parser.add_argument("--r2", action="store_true", help="Clean only the R2 bucket")
    clean_parser.add_argument("--d1", action="store_true", help="Clean only the D1 database")
    clean_parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    clean_parser.add_argument("--backup", action="store_true", help="Create a backup before cleaning")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up temporary files and directories")
    cleanup_parser.add_argument("--force", action="store_true", help="Force cleanup without confirmation")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    cleanup_parser.add_argument("--deep-clean", action="store_true", help="Perform a deep clean (including node_modules)")
    cleanup_parser.add_argument("--backup", action="store_true", help="Create a backup before cleaning")
    
    # Clean backups command
    clean_backups_parser = subparsers.add_parser("clean-backups", help="Clean old backup directories")
    clean_backups_parser.add_argument("--max-backups", type=int, default=5, help="Maximum number of backups to keep (default: 5)")
    clean_backups_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    clean_backups_parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    clean_backups_parser.add_argument("--backup-dir", type=str, default="backups", help="Backup directory (default: backups)")
    
    # Help command
    subparsers.add_parser("help", help="Show detailed help information")
    
    args = parser.parse_args()
    
    # If no command is provided or help command is used, show help
    if args.command is None or args.command == "help":
        show_help()
        return 0
    
    # Execute the appropriate command
    try:
        if args.command == "extract-catalog":
            return extract_catalog_main(args)
        elif args.command == "update-prices":
            return update_prices_main(args)
        elif args.command == "setup-db":
            return setup_db_main(args)
        elif args.command == "export":
            return export_main(args)
        elif args.command == "clean":
            return clean_main(args)
        elif args.command == "cleanup":
            return cleanup_main(args)
        elif args.command == "clean-backups":
            return clean_old_backups(
                backup_dir=args.backup_dir,
                max_backups=args.max_backups,
                dry_run=args.dry_run,
                force=args.force
            )
        else:
            print(f"Unknown command: {args.command}")
            return 1
    except Exception as e:
        print(f"Error executing command {args.command}: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 