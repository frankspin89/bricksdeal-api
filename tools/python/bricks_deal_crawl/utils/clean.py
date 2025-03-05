#!/usr/bin/env python3

import os
import boto3
import subprocess
import argparse
from dotenv import load_dotenv
import sys
import time
import shutil
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Constants
CLOUDFLARE_ENDPOINT = f"https://{os.environ.get('CLOUDFLARE_ACCOUNT_ID')}.r2.cloudflarestorage.com"
CLOUDFLARE_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")
CLOUDFLARE_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")
CLOUDFLARE_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET", "lego-images")
CLOUDFLARE_DATABASE_ID = os.environ.get("CLOUDFLARE_DATABASE_ID")
CLOUDFLARE_DATABASE_NAME = "bricksdeal"

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

def create_backup(files_to_backup):
    """Create a backup of important files."""
    # Create the main backups directory if it doesn't exist
    main_backup_dir = "backups"
    ensure_directory(main_backup_dir)
    
    # Create a timestamped subdirectory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(main_backup_dir, f"cloudflare_backup_{timestamp}")
    ensure_directory(backup_dir)
    
    # Backup files
    backed_up_files = backup_files(files_to_backup, backup_dir)
    
    if backed_up_files > 0:
        print_success(f"Backed up {backed_up_files} files to {backup_dir}")
        print_success(f"Note: Sensitive information has been redacted from configuration files.")
        return backup_dir
    else:
        print_warning("No files were backed up.")
        # Remove the empty backup directory
        if os.path.exists(backup_dir) and not os.listdir(backup_dir):
            os.rmdir(backup_dir)
            print_step(f"Removed empty backup directory: {backup_dir}")
        return None

def clean_r2_bucket(force=False):
    """Clean the R2 bucket by deleting all objects."""
    print_header(f"Cleaning R2 bucket: {CLOUDFLARE_BUCKET_NAME}")
    
    # Check if boto3 is available
    try:
        import boto3
    except ImportError:
        print_error("boto3 is not installed. Please install it with: pip install boto3")
        return False
    
    # Check if Cloudflare credentials are available
    if not CLOUDFLARE_ACCESS_KEY_ID or not CLOUDFLARE_SECRET_ACCESS_KEY or not CLOUDFLARE_ENDPOINT:
        print_error("Cloudflare R2 credentials not set. Please set the following environment variables:")
        print("  - CLOUDFLARE_ACCOUNT_ID")
        print("  - CLOUDFLARE_ACCESS_KEY_ID")
        print("  - CLOUDFLARE_SECRET_ACCESS_KEY")
        return False
    
    # Confirm action if not forced
    if not force:
        if not confirm_action(f"Are you sure you want to delete ALL objects in the {CLOUDFLARE_BUCKET_NAME} bucket?"):
            print_warning("Operation cancelled by user.")
            return False
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url=CLOUDFLARE_ENDPOINT,
            aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
            aws_secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY
        )
        
        # List all objects in the bucket
        print_step("Listing objects in the bucket...")
        response = s3.list_objects_v2(Bucket=CLOUDFLARE_BUCKET_NAME)
        
        if 'Contents' not in response:
            print_success("No objects found in the bucket.")
            return True
        
        objects = response['Contents']
        print_step(f"Found {len(objects)} objects in the bucket.")
        
        # Delete all objects with a progress indicator
        total_objects = len(objects)
        deleted_objects = 0
        
        for obj in objects:
            key = obj['Key']
            s3.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=key)
            deleted_objects += 1
            
            # Print progress
            progress = (deleted_objects / total_objects) * 100
            print(f"\rDeleting objects... {progress:.1f}% ({deleted_objects}/{total_objects})", end="")
            sys.stdout.flush()
        
        print()  # New line after progress indicator
        
        # Check if there are more objects (pagination)
        while response.get('IsTruncated', False):
            continuation_token = response.get('NextContinuationToken')
            response = s3.list_objects_v2(
                Bucket=CLOUDFLARE_BUCKET_NAME,
                ContinuationToken=continuation_token
            )
            
            if 'Contents' in response:
                objects = response['Contents']
                additional_objects = len(objects)
                total_objects += additional_objects
                print_step(f"Found {additional_objects} more objects in the bucket.")
                
                for obj in objects:
                    key = obj['Key']
                    s3.delete_object(Bucket=CLOUDFLARE_BUCKET_NAME, Key=key)
                    deleted_objects += 1
                    
                    # Print progress
                    progress = (deleted_objects / total_objects) * 100
                    print(f"\rDeleting objects... {progress:.1f}% ({deleted_objects}/{total_objects})", end="")
                    sys.stdout.flush()
                
                print()  # New line after progress indicator
        
        print_success(f"Successfully cleaned the R2 bucket. Deleted {deleted_objects} objects.")
        return True
    except Exception as e:
        print_error(f"Error cleaning R2 bucket: {str(e)}")
        return False

def clean_d1_database(force=False):
    """Clean the D1 database by dropping all tables."""
    print_header(f"Cleaning D1 database: {CLOUDFLARE_DATABASE_NAME}")
    
    # Check if wrangler is available
    try:
        subprocess.run(["npx", "wrangler", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print_error("Wrangler is not available. Please install it with: npm install -g wrangler")
        return False
    
    # Confirm action if not forced
    if not force:
        if not confirm_action(f"Are you sure you want to DROP ALL TABLES in the {CLOUDFLARE_DATABASE_NAME} database?"):
            print_warning("Operation cancelled by user.")
            return False
    
    try:
        # SQL command to drop all tables
        drop_tables_sql = """
        DROP TABLE IF EXISTS metadata;
        DROP TABLE IF EXISTS images;
        DROP TABLE IF EXISTS prices;
        DROP TABLE IF EXISTS minifigures;
        DROP TABLE IF EXISTS set_themes;
        DROP TABLE IF EXISTS lego_sets;
        DROP TABLE IF EXISTS themes;
        """
        
        # Execute the SQL command using wrangler
        print_step("Executing SQL command to drop all tables...")
        result = subprocess.run(
            [
                "npx", 
                "wrangler", 
                "d1", 
                "execute", 
                CLOUDFLARE_DATABASE_NAME, 
                "--command", 
                drop_tables_sql,
                "--remote"
            ],
            check=True,
            capture_output=True,
            text=True
        )
        
        print_success("Successfully cleaned the D1 database.")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error cleaning D1 database: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return False
    except Exception as e:
        print_error(f"Error cleaning D1 database: {str(e)}")
        return False

def main(args=None):
    """Main function to clean R2 bucket and D1 database."""
    if args is None:
        parser = argparse.ArgumentParser(description="Clean Cloudflare R2 bucket and D1 database")
        parser.add_argument("--r2", action="store_true", help="Clean R2 bucket")
        parser.add_argument("--d1", action="store_true", help="Clean D1 database")
        parser.add_argument("--force", action="store_true", help="Force cleaning without confirmation")
        parser.add_argument("--backup", action="store_true", help="Create a backup before cleaning")
        
        args = parser.parse_args()
    
    # If no specific option is provided, clean both
    if not args.r2 and not args.d1:
        args.r2 = True
        args.d1 = True
    
    # Set default values if not present in args
    force = getattr(args, 'force', False)
    backup = getattr(args, 'backup', False)
    
    # Print welcome message
    print_header("Bricks Deal Cloudflare Resource Cleaner")
    print(f"{Colors.CYAN}This tool will clean Cloudflare resources used by the Bricks Deal application.{Colors.ENDC}")
    print(f"{Colors.CYAN}Resources to clean:{Colors.ENDC}")
    if args.r2:
        print(f"{Colors.CYAN}- R2 bucket: {CLOUDFLARE_BUCKET_NAME}{Colors.ENDC}")
    if args.d1:
        print(f"{Colors.CYAN}- D1 database: {CLOUDFLARE_DATABASE_NAME}{Colors.ENDC}")
    print()
    
    # Backup functionality
    if backup:
        print_header("Creating Backup")
        files_to_backup = [
            "schema.sql",
            "apps/api/wrangler.toml",
            ".env"
        ]
        create_backup(files_to_backup)
    
    success = True
    
    if args.r2:
        r2_success = clean_r2_bucket(force)
        if not r2_success:
            success = False
    
    if args.d1:
        d1_success = clean_d1_database(force)
        if not d1_success:
            success = False
    
    # Print summary
    print_header("Cleaning Summary")
    if success:
        print_success("All cleaning operations completed successfully.")
    else:
        print_warning("Some cleaning operations failed. Please check the logs above for details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    main() 