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
    
    # Update prices
    prices_parser = subparsers.add_parser("update-prices", help="Update LEGO prices")
    prices_parser.add_argument("--set-num", type=str, help="LEGO set number to update")
    
    # Setup database
    db_parser = subparsers.add_parser("setup-db", help="Setup the database")
    db_parser.add_argument("--clean", action="store_true", help="Clean the database before setup")
    
    # Export data
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("--target", choices=["cloudflare", "d1"], required=True, help="Export target")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Import and run the appropriate module
    try:
        if args.command == "extract-catalog":
            from .catalog.extract import main as extract_main
            return extract_main(args)
        elif args.command == "update-prices":
            from .utils.update_prices import main as prices_main
            return prices_main(args)
        elif args.command == "setup-db":
            if args.clean:
                from .database.clean import main as clean_main
                return clean_main(args)
            else:
                from .database.setup import main as setup_main
                return setup_main(args)
        elif args.command == "export":
            if args.target == "cloudflare":
                from .export.cloudflare import main as cloudflare_main
                return cloudflare_main(args)
            elif args.target == "d1":
                from .export.d1 import main as d1_main
                return d1_main(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 