#!/usr/bin/env python3
"""
Main entry point for the Bricks Deal Crawl package.
"""

import argparse
import sys
from importlib import import_module


def main():
    """Main entry point for the Bricks Deal Crawl package."""
    parser = argparse.ArgumentParser(
        description="Bricks Deal Crawl - LEGO data processing and catalog management tools"
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract catalog data
    extract_parser = subparsers.add_parser("extract-catalog", help="Extract LEGO catalog data")
    extract_parser.add_argument("--extract-only", action="store_true", help="Only extract .gz files without processing images")
    extract_parser.add_argument("--process-images", action="store_true", help="Process images without extracting .gz files")
    extract_parser.add_argument("--update-csv", action="store_true", help="Update CSV files with new image URLs")
    extract_parser.add_argument("--limit", type=int, help="Limit the number of images to process")
    extract_parser.add_argument("--minifigs-only", action="store_true", help="Process only minifigure images")
    extract_parser.add_argument("--test", action="store_true", help="Run test function for multiple images")
    extract_parser.add_argument("--use-proxies", action="store_true", help="Use proxy rotation for image downloads")
    extract_parser.add_argument("--proxies-file", type=str, default="input/proxies.csv", help="File containing proxy URLs")
    extract_parser.add_argument("--start-index", type=int, default=0, help="Start index for batch processing")
    extract_parser.add_argument("--batch-size", type=int, default=0, help="Batch size for processing (0 means process all)")
    extract_parser.add_argument("--rebuild-mapping", action="store_true", help="Rebuild image mapping from catalog-images directory")
    extract_parser.add_argument("--force-upload", action="store_true", help="Force upload all images to Cloudflare R2 when rebuilding mapping")
    extract_parser.add_argument("--test-proxy", action="store_true", help="Test proxy configuration")
    extract_parser.add_argument("--force-own-ip", action="store_true", help="Allow using your own IP address if no proxy is available")
    
    # Continue extraction (new command)
    continue_parser = subparsers.add_parser("continue-extract", help="Continue extracting LEGO catalog data from where you left off")
    continue_parser.add_argument("--type", choices=["minifigs", "sets"], default="minifigs",
                        help="Type of items to process (default: minifigs)")
    continue_parser.add_argument("--batch-size", type=int, default=100,
                        help="Number of items to process in this batch (default: 100)")
    continue_parser.add_argument("--no-proxies", action="store_true",
                        help="Disable proxy rotation for image downloads")
    continue_parser.add_argument("--proxies-file", type=str, default="input/proxies.csv",
                        help="File containing proxy URLs")
    continue_parser.add_argument("--no-update-csv", action="store_true",
                        help="Don't update CSV files with new image URLs")
    continue_parser.add_argument("--reset", action="store_true",
                        help="Reset progress tracking and start from the beginning")
    continue_parser.add_argument("--reset-type", choices=["minifigs", "sets"],
                        help="Reset progress for a specific item type")
    continue_parser.add_argument("--show", action="store_true",
                        help="Show current progress without running extraction")
    
    # Interactive mode (new command)
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive CLI menu")
    
    # Update prices
    prices_parser = subparsers.add_parser("update-prices", help="Update LEGO prices")
    prices_parser.add_argument("--set-num", type=str, help="LEGO set number to update")
    
    # Setup database
    db_parser = subparsers.add_parser("setup-db", help="Setup the database")
    db_parser.add_argument("--clean", action="store_true", help="Clean the database before setup")
    
    # Export data
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("--target", choices=["cloudflare", "d1"], required=True, help="Export target")
    
    # Clean Cloudflare resources
    clean_parser = subparsers.add_parser("clean", help="Clean Cloudflare R2 bucket and D1 database")
    clean_parser.add_argument("--r2", action="store_true", help="Clean R2 bucket")
    clean_parser.add_argument("--d1", action="store_true", help="Clean D1 database")
    clean_parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    clean_parser.add_argument("--backup", action="store_true", help="Create a backup before cleaning (not implemented yet)")
    
    # Cleanup temporary files
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up temporary files and directories")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    cleanup_parser.add_argument("--backup", action="store_true", help="Backup files before removing them")
    cleanup_parser.add_argument("--deep-clean", action="store_true", help="Perform a deeper cleanup, removing temporary files")
    cleanup_parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    
    # Clean backups command
    clean_backups_parser = subparsers.add_parser("clean-backups", help="Clean old backup directories")
    clean_backups_parser.add_argument("--max-backups", type=int, default=5, help="Maximum number of backups to keep (default: 5)")
    clean_backups_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually doing it")
    clean_backups_parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
    clean_backups_parser.add_argument("--backup-dir", type=str, default="backups", help="Backup directory (default: backups)")
    
    # Help command
    help_parser = subparsers.add_parser("help", help="Show detailed help and usage information")
    help_parser.add_argument("--command", type=str, help="Show help for a specific command")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        # If no command is provided, show the help
        from bricks_deal_crawl.utils.help import show_help
        show_help()
        return 0
    
    # Import and run the appropriate module
    try:
        if args.command == "extract-catalog":
            from bricks_deal_crawl.catalog.extract import main as extract_main
            return extract_main(args)
        elif args.command == "continue-extract":
            from bricks_deal_crawl.catalog.continue_extract import main as continue_main
            return continue_main(args)
        elif args.command == "interactive":
            from bricks_deal_crawl.utils.interactive import main as interactive_main
            return interactive_main()
        elif args.command == "update-prices":
            from bricks_deal_crawl.utils.update_prices import main as prices_main
            return prices_main(args)
        elif args.command == "setup-db":
            if args.clean:
                from bricks_deal_crawl.database.clean import main as clean_main
                return clean_main(args)
            else:
                from bricks_deal_crawl.database.setup import main as setup_main
                return setup_main(args)
        elif args.command == "export":
            if args.target == "cloudflare":
                from bricks_deal_crawl.export.cloudflare import main as cloudflare_main
                return cloudflare_main(args)
            elif args.target == "d1":
                from bricks_deal_crawl.export.d1 import main as d1_main
                return d1_main(args)
        elif args.command == "clean":
            from bricks_deal_crawl.utils.clean import main as clean_main
            return clean_main(args)
        elif args.command == "cleanup":
            from bricks_deal_crawl.utils.cleanup import main as cleanup_main
            return cleanup_main(args)
        elif args.command == "clean-backups":
            from bricks_deal_crawl.utils.clean_backups import clean_old_backups
            return clean_old_backups(
                backup_dir=args.backup_dir,
                max_backups=args.max_backups,
                dry_run=args.dry_run,
                force=args.force
            )
        elif args.command == "help":
            from bricks_deal_crawl.utils.help import main as help_main
            return help_main(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 