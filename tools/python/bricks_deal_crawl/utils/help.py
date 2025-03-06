#!/usr/bin/env python3
"""
Help module for the Bricks Deal Crawl package.
"""

import os
import sys
import argparse

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(message):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}\n")

def print_command(command, description, options=None):
    """Print a formatted command with its description and options."""
    print(f"{Colors.GREEN}{Colors.BOLD}bricks-deal {command}{Colors.ENDC}")
    print(f"  {description}")
    
    if options:
        print(f"  {Colors.BLUE}Options:{Colors.ENDC}")
        for option, desc in options.items():
            print(f"    {Colors.YELLOW}{option}{Colors.ENDC}: {desc}")
    
    print()

def print_workflow_step(number, title, commands):
    """Print a workflow step with its commands."""
    print(f"{Colors.CYAN}{Colors.BOLD}{number}. {title}{Colors.ENDC}")
    for cmd in commands:
        print(f"   {Colors.GREEN}${Colors.ENDC} {cmd}")
    print()

def show_help():
    """Show a nice overview of all available commands."""
    # Clear the screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Print the logo
    print(f"""
{Colors.CYAN}{Colors.BOLD}
 ____       _      _          ____             _ 
| __ ) _ __(_) ___| | _____  |  _ \  ___  __ _| |
|  _ \| '__| |/ __| |/ / __| | | | |/ _ \/ _` | |
| |_) | |  | | (__|   <\__ \ | |_| |  __/ (_| | |
|____/|_|  |_|\___|_|\_\___/ |____/ \___|\__,_|_|
                                                 
{Colors.ENDC}""")
    
    print_header("LEGO Data Processing and Catalog Management Tools")
    
    print(f"{Colors.CYAN}This tool provides commands for processing LEGO catalog data, managing prices,")
    print(f"setting up databases, and exporting data to Cloudflare.{Colors.ENDC}")
    print()
    
    # Commands section
    print_header("Available Commands")
    
    print_command("extract-catalog", "Extract and process LEGO catalog data", {
        "--extract-only": "Only extract .gz files without processing images",
        "--process-images": "Process images without extracting .gz files",
        "--update-csv": "Update CSV files with new image URLs",
        "--limit N": "Limit the number of images to process",
        "--minifigs-only": "Process only minifigure images",
        "--use-proxies": "Use proxy rotation for image downloads",
        "--proxies-file FILE": "File containing proxy URLs (default: input/proxies.csv)",
        "--start-index N": "Start index for batch processing (default: 0)",
        "--batch-size N": "Batch size for processing (0 means process all)"
    })
    
    print_command("continue-extract", "Continue extracting LEGO catalog data from where you left off", {
        "--type TYPE": "Type of items to process: minifigs or sets (default: minifigs)",
        "--batch-size N": "Number of items to process in this batch (default: 100)",
        "--no-proxies": "Disable proxy rotation for image downloads",
        "--proxies-file FILE": "File containing proxy URLs (default: input/proxies.csv)",
        "--no-update-csv": "Don't update CSV files with new image URLs",
        "--reset": "Reset progress tracking and start from the beginning",
        "--reset-type TYPE": "Reset progress for a specific item type (minifigs or sets)",
        "--show": "Show current progress without running extraction"
    })
    
    print_command("interactive", "Start interactive CLI menu", {})
    
    print_command("update-prices", "Update prices for LEGO products", {
        "--set-num NUMBER": "LEGO set number to update (e.g., 10353)"
    })
    
    print_command("setup-db", "Set up the LEGO catalog database", {
        "--clean": "Clean the database before setup"
    })
    
    print_command("export", "Export LEGO catalog data to various targets", {
        "--target cloudflare": "Export to Cloudflare R2",
        "--target d1": "Export to Cloudflare D1"
    })
    
    print_command("clean", "Clean Cloudflare R2 bucket and D1 database", {
        "--r2": "Clean only R2 bucket",
        "--d1": "Clean only D1 database",
        "--force": "Force cleaning without confirmation",
        "--backup": "Create a backup before cleaning"
    })
    
    print_command("cleanup", "Clean up temporary files and directories", {
        "--dry-run": "Show what would be done without actually doing it",
        "--backup": "Backup files before removing them",
        "--deep-clean": "Perform a deeper cleanup, removing temporary files",
        "--force": "Force cleaning without confirmation"
    })
    
    print_command("clean-backups", "Clean old backup directories, keeping only the most recent ones", {
        "--max-backups N": "Maximum number of backups to keep (default: 5)",
        "--dry-run": "Show what would be done without actually doing it",
        "--force": "Force cleaning without confirmation",
        "--backup-dir DIR": "Backup directory (default: backups)"
    })
    
    # Workflow section
    print_header("Common Workflows")
    
    print(f"{Colors.BOLD}Initial Setup{Colors.ENDC}")
    print_workflow_step("1", "Install the package in development mode", [
        "pip install -e ."
    ])
    
    print_workflow_step("2", "Extract and prepare catalog data", [
        "bricks-deal extract-catalog"
    ])
    
    print_workflow_step("3", "Set up the database", [
        "bricks-deal setup-db --clean"
    ])
    
    print_workflow_step("4", "Export to Cloudflare D1", [
        "bricks-deal export --target d1"
    ])
    
    print(f"{Colors.BOLD}Regular Updates{Colors.ENDC}")
    print_workflow_step("1", "Update prices", [
        "bricks-deal update-prices"
    ])
    
    print_workflow_step("2", "Update Cloudflare D1", [
        "bricks-deal export --target d1"
    ])
    
    print(f"{Colors.BOLD}Maintenance{Colors.ENDC}")
    print_workflow_step("1", "Clean up temporary files", [
        "bricks-deal cleanup"
    ])
    
    print_workflow_step("2", "Clean Cloudflare resources", [
        "bricks-deal clean"
    ])
    
    print_workflow_step("3", "Manage backup directories", [
        "bricks-deal clean-backups --max-backups 3"
    ])
    
    print()
    print(f"{Colors.CYAN}For more detailed information, run:{Colors.ENDC}")
    print(f"  {Colors.GREEN}bricks-deal [command] --help{Colors.ENDC}")
    print()

def main(args=None):
    """Main function to show help."""
    if args is None:
        parser = argparse.ArgumentParser(description="Show help for Bricks Deal Crawl")
        parser.add_argument("--command", type=str, help="Show help for a specific command")
        
        args = parser.parse_args()
    
    show_help()
    return 0

if __name__ == "__main__":
    main() 