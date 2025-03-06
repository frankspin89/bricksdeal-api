#!/usr/bin/env python3
"""
Module for continuous extraction of LEGO catalog data.
"""

import os
import json
import argparse
from pathlib import Path

# Path to store the progress tracking file
PROGRESS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "input", "extract_progress.json"
)

def load_progress():
    """Load the current progress from the progress file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not read progress file. Starting from beginning.")
    
    # Default progress data
    return {
        "minifigs": {
            "last_index": 0,
            "total_processed": 0
        },
        "sets": {
            "last_index": 0,
            "total_processed": 0
        }
    }

def save_progress(progress):
    """Save the current progress to the progress file."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except IOError:
        print(f"Warning: Could not save progress to {PROGRESS_FILE}")

def continue_extraction(item_type, batch_size, use_proxies=True, proxies_file=None, update_csv=True):
    """Continue extraction from where we left off."""
    from bricks_deal_crawl.catalog.extract import main as extract_main
    
    # Load progress
    progress = load_progress()
    
    # Determine the start index based on the item type
    start_index = progress[item_type]["last_index"]
    
    print(f"Continuing {item_type} extraction from index {start_index}")
    print(f"Batch size: {batch_size}")
    
    # Set default value for proxies_file if None
    if proxies_file is None:
        proxies_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "input", "proxies.csv"
        )
    
    # Create args object to pass to extract_main
    class Args:
        pass
    
    args = Args()
    args.extract_only = False
    args.process_images = False
    args.update_csv = update_csv
    args.limit = None
    args.minifigs_only = (item_type == "minifigs")
    args.test = False
    args.use_proxies = use_proxies
    args.proxies_file = proxies_file
    args.start_index = start_index
    args.batch_size = batch_size
    args.force_own_ip = False
    args.rebuild_mapping = False
    args.force_upload = False
    args.test_proxy = False
    args.dry_run = False
    args.validate_urls = False
    args.validate_all = False
    args.verify_r2 = False
    args.cleanup_local = False
    args.continue_processing = False
    args.show_progress = False
    
    # Run the extraction
    extract_main(args)
    
    # Update progress
    progress[item_type]["last_index"] += batch_size
    progress[item_type]["total_processed"] += batch_size
    save_progress(progress)
    
    print(f"\nProgress updated: {item_type} processed up to index {progress[item_type]['last_index']}")
    print(f"Total {item_type} processed so far: {progress[item_type]['total_processed']}")

def reset_progress(item_type=None):
    """Reset the progress tracking."""
    progress = load_progress()
    
    if item_type:
        if item_type in progress:
            progress[item_type]["last_index"] = 0
            progress[item_type]["total_processed"] = 0
            print(f"Progress for {item_type} has been reset.")
        else:
            print(f"Unknown item type: {item_type}")
    else:
        # Reset all progress
        for key in progress:
            progress[key]["last_index"] = 0
            progress[key]["total_processed"] = 0
        print("All progress has been reset.")
    
    save_progress(progress)

def show_progress():
    """Show the current progress."""
    progress = load_progress()
    
    print("\nCurrent Progress:")
    print("-----------------")
    for item_type, data in progress.items():
        print(f"{item_type.capitalize()}:")
        print(f"  Next start index: {data['last_index']}")
        print(f"  Total processed: {data['total_processed']}")
    print()

def main(args):
    """Main entry point for the continue-extract command."""
    # Show progress if requested
    if args.show:
        show_progress()
        return
    
    # Reset progress if requested
    if args.reset:
        reset_progress()
        return
    
    if args.reset_type:
        reset_progress(args.reset_type)
        return
    
    # Run the extraction
    continue_extraction(
        item_type=args.type,
        batch_size=args.batch_size,
        use_proxies=not args.no_proxies,
        proxies_file=args.proxies_file,
        update_csv=not args.no_update_csv
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Continue extracting LEGO catalog data from where you left off")
    parser.add_argument("--type", choices=["minifigs", "sets"], default="minifigs",
                        help="Type of items to process (default: minifigs)")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Number of items to process in this batch (default: 100)")
    parser.add_argument("--no-proxies", action="store_true",
                        help="Disable proxy rotation for image downloads")
    parser.add_argument("--proxies-file", 
                        help="File containing proxy URLs (default: input/proxies.csv)")
    parser.add_argument("--no-update-csv", action="store_true",
                        help="Don't update CSV files with new image URLs")
    parser.add_argument("--reset", action="store_true",
                        help="Reset progress tracking and start from the beginning")
    parser.add_argument("--reset-type", choices=["minifigs", "sets"],
                        help="Reset progress for a specific item type")
    parser.add_argument("--show", action="store_true",
                        help="Show current progress without running extraction")
    
    args = parser.parse_args()
    main(args) 