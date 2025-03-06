#!/usr/bin/env python3
"""
Interactive CLI menu for Bricks Deal.
"""

import os
import sys
import time
from .help import Colors

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print a header with the given title."""
    clear_screen()
    print(f"""
{Colors.CYAN}{Colors.BOLD}
 ____       _      _          ____             _ 
| __ ) _ __(_) ___| | _____  |  _ \  ___  __ _| |
|  _ \| '__| |/ __| |/ / __| | | | |/ _ \/ _` | |
| |_) | |  | | (__|   <\__ \ | |_| |  __/ (_| | |
|____/|_|  |_|\___|_|\_\___/ |____/ \___|\__,_|_|
                                                 
{Colors.ENDC}""")
    print(f"{Colors.YELLOW}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * len(title)}{Colors.ENDC}\n")

def print_menu_item(index, title, description=None):
    """Print a menu item with the given index and title."""
    print(f"{Colors.GREEN}{index}.{Colors.ENDC} {Colors.BOLD}{title}{Colors.ENDC}")
    if description:
        print(f"   {Colors.CYAN}{description}{Colors.ENDC}")

def print_back_option():
    """Print the back option."""
    print(f"\n{Colors.RED}b.{Colors.ENDC} {Colors.BOLD}Back{Colors.ENDC}")

def print_exit_option():
    """Print the exit option."""
    print(f"{Colors.RED}q.{Colors.ENDC} {Colors.BOLD}Quit{Colors.ENDC}")

def get_user_choice(options):
    """Get the user's choice from the given options."""
    while True:
        choice = input(f"\n{Colors.YELLOW}Enter your choice: {Colors.ENDC}").strip().lower()
        if choice in options:
            return choice
        print(f"{Colors.RED}Invalid choice. Please try again.{Colors.ENDC}")

def loading_animation(message, duration=1.5):
    """Show a loading animation with the given message."""
    chars = "|/-\\"
    for _ in range(int(duration * 10)):
        for char in chars:
            sys.stdout.write(f"\r{message} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write(f"\r{message} Done!{' ' * 10}\n")

def run_command(command, args=None):
    """Run a command with the given arguments."""
    if args is None:
        args = []
    
    # Convert args to a list of strings
    args = [str(arg) for arg in args]
    
    # Build the command string
    cmd = f"bricks-deal {command} {' '.join(args)}"
    
    # Print the command
    print(f"\n{Colors.CYAN}Running: {cmd}{Colors.ENDC}\n")
    
    # Run the command
    os.system(cmd)
    
    # Wait for user to press enter
    input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.ENDC}")

def extract_catalog_menu():
    """Show the extract catalog menu."""
    while True:
        print_header("Extract Catalog Menu")
        
        print_menu_item(1, "Extract Catalog Data", "Extract raw catalog data from .gz files")
        print_menu_item(2, "Process Images", "Download and process images")
        print_menu_item(3, "Update CSV Files", "Update CSV files with new image URLs")
        print_menu_item(4, "Continue Extraction", "Continue from where you left off")
        print_menu_item(5, "Show Extraction Progress", "Show current extraction progress")
        print_menu_item(6, "Reset Extraction Progress", "Reset extraction progress tracking")
        print_menu_item(7, "Rebuild Image Mapping", "Rebuild image mapping from catalog-images directory")
        print_menu_item(8, "Test Proxy Configuration", "Test if proxies are working correctly")
        
        print_back_option()
        print_exit_option()
        
        choice = get_user_choice(['1', '2', '3', '4', '5', '6', '7', '8', 'b', 'q'])
        
        if choice == '1':
            extract_only_menu()
        elif choice == '2':
            process_images_menu()
        elif choice == '3':
            update_csv_menu()
        elif choice == '4':
            continue_extraction_menu()
        elif choice == '5':
            run_command("continue-extract", ["--show"])
        elif choice == '6':
            reset_progress_menu()
        elif choice == '7':
            rebuild_mapping_menu()
        elif choice == '8':
            test_proxy_menu()
        elif choice == 'b':
            return
        elif choice == 'q':
            sys.exit(0)

def extract_only_menu():
    """Show the extract only menu."""
    print_header("Extract Only Menu")
    
    print_menu_item(1, "Extract All", "Extract all catalog data")
    print_menu_item(2, "Extract with Options", "Extract with custom options")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', 'b'])
    
    if choice == '1':
        run_command("extract-catalog", ["--extract-only"])
    elif choice == '2':
        # Get custom options
        use_proxies = input(f"{Colors.YELLOW}Use proxies? (y/n): {Colors.ENDC}").strip().lower() == 'y'
        
        args = ["--extract-only"]
        if use_proxies:
            args.append("--use-proxies")
            proxies_file = input(f"{Colors.YELLOW}Proxies file (leave empty for default): {Colors.ENDC}").strip()
            if proxies_file:
                args.extend(["--proxies-file", proxies_file])
        
        run_command("extract-catalog", args)

def process_images_menu():
    """Show the process images menu."""
    print_header("Process Images Menu")
    
    print_menu_item(1, "Process All Images", "Process all catalog images")
    print_menu_item(2, "Process Minifigs Only", "Process only minifigure images")
    print_menu_item(3, "Process with Limit", "Process with a limit on the number of images")
    print_menu_item(4, "Process with Batch Options", "Process with batch options")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', '3', '4', 'b'])
    
    args = ["--process-images"]
    
    if choice == '1':
        pass  # Use default args
    elif choice == '2':
        args.append("--minifigs-only")
    elif choice == '3':
        args.append("--minifigs-only")
        limit = input(f"{Colors.YELLOW}Limit (number of images): {Colors.ENDC}").strip()
        if limit:
            args.extend(["--limit", limit])
    elif choice == '4':
        args.append("--minifigs-only")
        start_index = input(f"{Colors.YELLOW}Start index: {Colors.ENDC}").strip()
        if start_index:
            args.extend(["--start-index", start_index])
        
        batch_size = input(f"{Colors.YELLOW}Batch size: {Colors.ENDC}").strip()
        if batch_size:
            args.extend(["--batch-size", batch_size])
    elif choice == 'b':
        return
    
    # Ask about proxies
    use_proxies = input(f"{Colors.YELLOW}Use proxies? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if use_proxies:
        args.append("--use-proxies")
        proxies_file = input(f"{Colors.YELLOW}Proxies file (leave empty for default): {Colors.ENDC}").strip()
        if proxies_file:
            args.extend(["--proxies-file", proxies_file])
        
        # Ask about allowing direct connections
        force_own_ip = input(f"{Colors.YELLOW}Allow using your own IP as fallback? (y/n): {Colors.ENDC}").strip().lower() == 'y'
        if force_own_ip:
            args.append("--force-own-ip")
    else:
        # If not using proxies, ask if they want to force using their own IP
        force_own_ip = input(f"{Colors.YELLOW}Force using your own IP? (y/n): {Colors.ENDC}").strip().lower() == 'y'
        if force_own_ip:
            args.append("--force-own-ip")
        else:
            print(f"{Colors.RED}Warning: Without proxies or --force-own-ip, image downloads will be skipped.{Colors.ENDC}")
            proceed = input(f"{Colors.YELLOW}Proceed anyway? (y/n): {Colors.ENDC}").strip().lower() == 'y'
            if not proceed:
                return
    
    run_command("extract-catalog", args)

def update_csv_menu():
    """Show the update CSV menu."""
    print_header("Update CSV Menu")
    
    print_menu_item(1, "Update All CSVs", "Update all CSV files")
    print_menu_item(2, "Update Minifigs Only", "Update only minifigure CSV")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', 'b'])
    
    args = ["--update-csv"]
    
    if choice == '1':
        pass  # Use default args
    elif choice == '2':
        args.append("--minifigs-only")
    elif choice == 'b':
        return
    
    # Ask about proxies
    use_proxies = input(f"{Colors.YELLOW}Use proxies? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if use_proxies:
        args.append("--use-proxies")
        proxies_file = input(f"{Colors.YELLOW}Proxies file (leave empty for default): {Colors.ENDC}").strip()
        if proxies_file:
            args.extend(["--proxies-file", proxies_file])
    
    run_command("extract-catalog", args)

def continue_extraction_menu():
    """Show the continue extraction menu."""
    print_header("Continue Extraction Menu")
    
    print_menu_item(1, "Continue Minifigs Extraction", "Continue extracting minifigs from where you left off")
    print_menu_item(2, "Continue Sets Extraction", "Continue extracting sets from where you left off")
    print_menu_item(3, "Custom Batch Size", "Continue extraction with a custom batch size")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', '3', 'b'])
    
    args = []
    
    if choice == '1':
        args.append("--type")
        args.append("minifigs")
    elif choice == '2':
        args.append("--type")
        args.append("sets")
    elif choice == '3':
        item_type = input(f"{Colors.YELLOW}Item type (minifigs/sets): {Colors.ENDC}").strip().lower()
        if item_type in ['minifigs', 'sets']:
            args.extend(["--type", item_type])
        else:
            print(f"{Colors.RED}Invalid item type. Using default (minifigs).{Colors.ENDC}")
            args.extend(["--type", "minifigs"])
        
        batch_size = input(f"{Colors.YELLOW}Batch size: {Colors.ENDC}").strip()
        if batch_size:
            args.extend(["--batch-size", batch_size])
    elif choice == 'b':
        return
    
    # Ask about proxies
    use_proxies = input(f"{Colors.YELLOW}Use proxies? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if not use_proxies:
        args.append("--no-proxies")
    else:
        proxies_file = input(f"{Colors.YELLOW}Proxies file (leave empty for default): {Colors.ENDC}").strip()
        if proxies_file:
            args.extend(["--proxies-file", proxies_file])
    
    # Ask about updating CSV
    update_csv = input(f"{Colors.YELLOW}Update CSV files? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if not update_csv:
        args.append("--no-update-csv")
    
    run_command("continue-extract", args)

def reset_progress_menu():
    """Show the reset progress menu."""
    print_header("Reset Progress Menu")
    
    print_menu_item(1, "Reset All Progress", "Reset all extraction progress")
    print_menu_item(2, "Reset Minifigs Progress", "Reset only minifigure extraction progress")
    print_menu_item(3, "Reset Sets Progress", "Reset only sets extraction progress")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', '3', 'b'])
    
    args = []
    
    if choice == '1':
        args.append("--reset")
    elif choice == '2':
        args.extend(["--reset-type", "minifigs"])
    elif choice == '3':
        args.extend(["--reset-type", "sets"])
    elif choice == 'b':
        return
    
    run_command("continue-extract", args)

def rebuild_mapping_menu():
    """Show the rebuild mapping menu."""
    print_header("Rebuild Image Mapping Menu")
    
    print_menu_item(1, "Rebuild Image Mapping", "Scan directory and update mapping file")
    print_menu_item(2, "Force Upload All Images", "Rebuild mapping and upload all images to Cloudflare R2")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', 'b'])
    
    if choice == '1':
        run_command("extract-catalog", ["--rebuild-mapping"])
    elif choice == '2':
        run_command("extract-catalog", ["--rebuild-mapping", "--force-upload"])
    elif choice == 'b':
        return

def database_menu():
    """Show the database menu."""
    print_header("Database Menu")
    
    print_menu_item(1, "Setup Database", "Set up the LEGO catalog database")
    print_menu_item(2, "Clean Database", "Clean the database before setup")
    
    print_back_option()
    print_exit_option()
    
    choice = get_user_choice(['1', '2', 'b', 'q'])
    
    if choice == '1':
        run_command("setup-db")
    elif choice == '2':
        run_command("setup-db", ["--clean"])
    elif choice == 'b':
        return
    elif choice == 'q':
        sys.exit(0)

def export_menu():
    """Show the export menu."""
    print_header("Export Menu")
    
    print_menu_item(1, "Export to Cloudflare", "Export to Cloudflare R2 and D1")
    print_menu_item(2, "Export to D1 Only", "Export to Cloudflare D1 only")
    
    print_back_option()
    print_exit_option()
    
    choice = get_user_choice(['1', '2', 'b', 'q'])
    
    if choice == '1':
        run_command("export", ["--target", "cloudflare"])
    elif choice == '2':
        run_command("export", ["--target", "d1"])
    elif choice == 'b':
        return
    elif choice == 'q':
        sys.exit(0)

def cleanup_menu():
    """Show the cleanup menu."""
    print_header("Cleanup Menu")
    
    print_menu_item(1, "Clean Cloudflare Resources", "Clean Cloudflare R2 bucket and D1 database")
    print_menu_item(2, "Clean Temporary Files", "Clean up temporary files and directories")
    print_menu_item(3, "Clean Old Backups", "Clean old backup directories")
    
    print_back_option()
    print_exit_option()
    
    choice = get_user_choice(['1', '2', '3', 'b', 'q'])
    
    if choice == '1':
        clean_cloudflare_menu()
    elif choice == '2':
        run_command("cleanup", ["--deep-clean"])
    elif choice == '3':
        max_backups = input(f"{Colors.YELLOW}Maximum number of backups to keep: {Colors.ENDC}").strip()
        if not max_backups:
            max_backups = "5"
        run_command("clean-backups", ["--max-backups", max_backups])
    elif choice == 'b':
        return
    elif choice == 'q':
        sys.exit(0)

def clean_cloudflare_menu():
    """Show the clean Cloudflare menu."""
    print_header("Clean Cloudflare Menu")
    
    print_menu_item(1, "Clean R2 Bucket", "Clean Cloudflare R2 bucket")
    print_menu_item(2, "Clean D1 Database", "Clean Cloudflare D1 database")
    print_menu_item(3, "Clean Both", "Clean both R2 bucket and D1 database")
    
    print_back_option()
    
    choice = get_user_choice(['1', '2', '3', 'b'])
    
    args = []
    
    if choice == '1':
        args.append("--r2")
    elif choice == '2':
        args.append("--d1")
    elif choice == '3':
        args.extend(["--r2", "--d1"])
    elif choice == 'b':
        return
    
    # Ask about force
    force = input(f"{Colors.YELLOW}Force cleaning without confirmation? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if force:
        args.append("--force")
    
    # Ask about backup
    backup = input(f"{Colors.YELLOW}Create a backup before cleaning? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if backup:
        args.append("--backup")
    
    run_command("clean", args)

def test_proxy_menu():
    """Show the test proxy menu."""
    print_header("Test Proxy Configuration")
    
    print("This will test if your proxy configuration is working correctly.")
    print("It will attempt to connect to a test URL using each configured proxy.")
    
    proxies_file = input(f"{Colors.YELLOW}Proxies file (leave empty for default): {Colors.ENDC}").strip()
    
    args = ["--test-proxy", "--use-proxies"]
    if proxies_file:
        args.extend(["--proxies-file", proxies_file])
    
    # Ask about allowing direct connections
    force_own_ip = input(f"{Colors.YELLOW}Allow using your own IP as fallback? (y/n): {Colors.ENDC}").strip().lower() == 'y'
    if force_own_ip:
        args.append("--force-own-ip")
    
    run_command("extract-catalog", args)

def main_menu():
    """Show the main menu."""
    while True:
        print_header("Main Menu")
        
        print_menu_item(1, "Extract Catalog", "Extract and process LEGO catalog data")
        print_menu_item(2, "Update Prices", "Update prices for LEGO products")
        print_menu_item(3, "Database Management", "Set up and manage the LEGO catalog database")
        print_menu_item(4, "Export Data", "Export LEGO catalog data to various targets")
        print_menu_item(5, "Cleanup Operations", "Clean up resources and temporary files")
        print_menu_item(6, "Help", "Show detailed help and usage information")
        
        print_exit_option()
        
        choice = get_user_choice(['1', '2', '3', '4', '5', '6', 'q'])
        
        if choice == '1':
            extract_catalog_menu()
        elif choice == '2':
            update_prices_menu()
        elif choice == '3':
            database_menu()
        elif choice == '4':
            export_menu()
        elif choice == '5':
            cleanup_menu()
        elif choice == '6':
            run_command("help")
        elif choice == 'q':
            print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
            sys.exit(0)

def update_prices_menu():
    """Show the update prices menu."""
    print_header("Update Prices Menu")
    
    print_menu_item(1, "Update All Prices", "Update prices for all sets")
    print_menu_item(2, "Update Specific Set", "Update price for a specific set")
    
    print_back_option()
    print_exit_option()
    
    choice = get_user_choice(['1', '2', 'b', 'q'])
    
    if choice == '1':
        run_command("update-prices")
    elif choice == '2':
        set_num = input(f"{Colors.YELLOW}Set number (e.g., 10423-1): {Colors.ENDC}").strip()
        if set_num:
            run_command("update-prices", ["--set-num", set_num])
        else:
            print(f"{Colors.RED}No set number provided. Returning to menu.{Colors.ENDC}")
            time.sleep(1.5)
    elif choice == 'b':
        return
    elif choice == 'q':
        sys.exit(0)

def main():
    """Main entry point for the interactive CLI."""
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}Operation cancelled by user.{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main() 