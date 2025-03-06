#!/usr/bin/env python3

import os
import gzip
import shutil
import csv
import argparse
import requests
import re
from urllib.parse import urlparse
from pathlib import Path
import concurrent.futures
from PIL import Image
import io
import boto3
import json
import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
LEGO_CATALOG_DIR = os.path.join("input", "lego-catalog")
EXTRACTED_DIR = os.path.join("input", "lego-catalog-extracted")
IMAGES_DIR = os.path.join("output", "catalog-images")
IMAGE_MAPPING_FILE = os.path.join(IMAGES_DIR, "image_mapping.json")

# Cloudflare R2 configuration
CLOUDFLARE_ENDPOINT = f"https://{os.environ.get('CLOUDFLARE_ACCOUNT_ID')}.r2.cloudflarestorage.com"
CLOUDFLARE_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")
CLOUDFLARE_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")
CLOUDFLARE_R2_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET", "lego-images")
CLOUDFLARE_PUBLIC_URL = f"https://{os.environ.get('CLOUDFLARE_DOMAIN', 'images.bricksdeal.com')}"

# Proxy configuration
PROXIES_FILE = os.path.join("input", "proxies.csv")
OXYLABS_USERNAME = os.environ.get("OXYLABS_USERNAME")
OXYLABS_PASSWORD = os.environ.get("OXYLABS_PASSWORD")
OXYLABS_ENDPOINT = os.environ.get("OXYLABS_ENDPOINT", "dc.oxylabs.io")  # Using datacenter proxies
try:
    OXYLABS_PORTS = [int(port.strip()) for port in os.environ.get("OXYLABS_PORTS", "8000").split(",") if port.strip().isdigit()]
    if not OXYLABS_PORTS:  # Fallback if no valid ports
        OXYLABS_PORTS = [8000]  # Default port for datacenter proxies
except Exception as e:
    print(f"Warning: Error parsing OXYLABS_PORTS: {e}. Using default ports.")
    OXYLABS_PORTS = [8000]  # Default port for datacenter proxies

class ProxyManager:
    """
    Manages a pool of proxies for rotation during requests.
    Tracks proxy success/failure and prioritizes working proxies.
    """
    def __init__(self, proxies_file: str = PROXIES_FILE, use_proxies: bool = False, force_own_ip: bool = False):
        self.proxies = []
        self.working_proxies = set()
        self.failed_proxies = {}
        self.use_proxies = use_proxies
        self.force_own_ip = force_own_ip
        self.current_index = 0
        
        if use_proxies:
            self.load_proxies(proxies_file)
            self.add_oxylabs_proxies()
            print(f"Loaded {len(self.proxies)} proxies")
    
    def add_oxylabs_proxies(self):
        """Add Oxylabs proxies to the proxy pool if credentials are available"""
        if not OXYLABS_USERNAME or not OXYLABS_PASSWORD:
            print("Warning: Oxylabs credentials not found in environment variables")
            return
        
        print(f"Adding Oxylabs proxies with username: {OXYLABS_USERNAME}")
        
        # Add the main port 8000 as shown in the curl example
        port = 8000
        # Check if username already contains the country/session part
        if "-country-" in OXYLABS_USERNAME or "-session-" in OXYLABS_USERNAME:
            # Add 'user-' prefix if not already present
            if not OXYLABS_USERNAME.startswith("user-"):
                username = f"user-{OXYLABS_USERNAME}"
            else:
                username = OXYLABS_USERNAME
        else:
            # Default to US if no country specified
            username = f"user-{OXYLABS_USERNAME}-country-US"
        
        # Create proxy URLs for both HTTP and HTTPS
        proxy_url = f"http://{username}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}:{port}"
        if proxy_url not in self.proxies:
            self.proxies.append(proxy_url)
            print(f"Added Oxylabs proxy on port {port}: {proxy_url}")
        
        # Also add the other ports if specified
        for port in OXYLABS_PORTS:
            if port == 8000:  # Skip if already added
                continue
            
            # Create proxy URLs for both HTTP and HTTPS
            proxy_url = f"http://{username}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}:{port}"
            if proxy_url not in self.proxies:
                self.proxies.append(proxy_url)
                print(f"Added Oxylabs proxy on port {port}: {proxy_url}")
    
    def load_proxies(self, proxies_file: str) -> None:
        """
        Load proxies from a CSV file.
        
        Args:
            proxies_file: Path to the CSV file containing proxy URLs
        """
        if not os.path.exists(proxies_file):
            print(f"Proxy file {proxies_file} not found. No proxies loaded.")
            return
        
        try:
            with open(proxies_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        proxy_url = row[0].strip()
                        if proxy_url not in self.proxies:
                            self.proxies.append(proxy_url)
        except Exception as e:
            print(f"Error loading proxies: {e}")
    
    def get_proxy(self) -> dict:
        """
        Get the next proxy in the rotation.
        Prioritizes working proxies over untested ones.
        
        Returns:
            Dictionary with proxy configuration for requests
        """
        if not self.use_proxies or not self.proxies:
            if not self.force_own_ip:
                print("WARNING: No proxies available and force_own_ip is not enabled. This request might fail.")
                print("Consider using --force-own-ip if you want to allow direct connections.")
            return {}
        
        # First try to use a working proxy if available
        if self.working_proxies:
            working_list = list(self.working_proxies)
            proxy_url = working_list[self.current_index % len(working_list)]
            self.current_index += 1
        else:
            # Otherwise, use the next proxy in the list, skipping known failed ones
            attempts = 0
            proxy_url = None
            
            while attempts < len(self.proxies):
                candidate = self.proxies[self.current_index % len(self.proxies)]
                self.current_index += 1
                
                # Skip proxies that have failed multiple times recently
                if candidate in self.failed_proxies and self.failed_proxies[candidate]["count"] > 2:
                    # Check if the failure is recent (within last hour)
                    last_failure = self.failed_proxies[candidate]["last_failure"]
                    if (datetime.datetime.now() - last_failure).total_seconds() < 3600:
                        attempts += 1
                        continue
                
                proxy_url = candidate
                break
            
            if proxy_url is None:
                if not self.force_own_ip:
                    print("WARNING: No suitable proxy found and force_own_ip is not enabled. This request might fail.")
                    print("Consider using --force-own-ip if you want to allow direct connections.")
                return {}  # No suitable proxy found
        
        # Parse the proxy URL to get the scheme and actual proxy address
        try:
            if proxy_url.startswith(('http://', 'https://')):
                scheme = proxy_url.split('://')[0]
                if OXYLABS_ENDPOINT in proxy_url:
                    # For Oxylabs, set both http and https
                    print(f"Using Oxylabs proxy: {proxy_url}")
                    # According to Oxylabs docs, we need to set both http and https
                    return {
                        "http": proxy_url,
                        "https": proxy_url
                    }
                else:
                    return {scheme: proxy_url}
            else:
                return {'http': f'http://{proxy_url}', 'https': f'https://{proxy_url}'}
        except Exception as e:
            print(f"Error parsing proxy URL {proxy_url}: {e}")
            return {}
    
    def mark_proxy_success(self, proxy_url: str) -> None:
        """
        Mark a proxy as working.
        
        Args:
            proxy_url: The proxy URL that was successful
        """
        if not proxy_url or not self.use_proxies:
            return
        
        # Add to working proxies set
        self.working_proxies.add(proxy_url)
        
        # Remove from failed proxies if present
        if proxy_url in self.failed_proxies:
            del self.failed_proxies[proxy_url]
            
        print(f"Proxy {proxy_url} marked as working")
    
    def mark_proxy_failure(self, proxy_url: str) -> None:
        """
        Mark a proxy as failed.
        
        Args:
            proxy_url: The proxy URL that failed
        """
        if not proxy_url or not self.use_proxies:
            return
        
        # Remove from working proxies if present
        if proxy_url in self.working_proxies:
            self.working_proxies.remove(proxy_url)
        
        # Add to failed proxies with timestamp and increment failure count
        now = datetime.datetime.now()
        if proxy_url in self.failed_proxies:
            self.failed_proxies[proxy_url]["count"] += 1
            self.failed_proxies[proxy_url]["last_failure"] = now
        else:
            self.failed_proxies[proxy_url] = {
                "count": 1,
                "last_failure": now
            }
            
        print(f"Proxy {proxy_url} marked as failed (count: {self.failed_proxies[proxy_url]['count']})")

# Initialize the proxy manager
proxy_manager = None

def ensure_directories():
    """Ensure all necessary directories exist."""
    os.makedirs(LEGO_CATALOG_DIR, exist_ok=True)
    os.makedirs(EXTRACTED_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

def extract_gz_files():
    """Extract all .gz files in the catalog directory to plain CSV files."""
    print("Extracting .gz files to plain CSV files...")
    
    # Get all .gz files in the catalog directory
    gz_files = [f for f in os.listdir(LEGO_CATALOG_DIR) if f.endswith('.csv.gz')]
    
    if not gz_files:
        print("No .gz files found in the catalog directory.")
        return
    
    for gz_file in gz_files:
        input_path = os.path.join(LEGO_CATALOG_DIR, gz_file)
        output_path = os.path.join(EXTRACTED_DIR, gz_file[:-3])  # Remove .gz extension
        
        print(f"Extracting {input_path} to {output_path}...")
        
        with gzip.open(input_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        print(f"Extracted {output_path}")
    
    print(f"Extracted {len(gz_files)} files to {EXTRACTED_DIR}")

def is_valid_image_url(url):
    """Check if a URL is likely to be an image."""
    if not url:
        return False
    
    # Check if the URL has an image extension
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    return any(path.endswith(ext) for ext in image_extensions)

def create_seo_friendly_filename(url, prefix="", name=""):
    """Create an SEO-friendly filename from a URL.
    
    Args:
        url (str): The original image URL
        prefix (str, optional): Prefix to add to the filename (e.g., set_num or fig_num)
        name (str, optional): Name of the set/minifig to include for SEO
    """
    # Extract the filename from the URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = os.path.basename(path)
    
    # Remove any query parameters
    filename = filename.split('?')[0]
    
    # Extract the file extension
    base_name, ext = os.path.splitext(filename)
    if not ext:
        ext = ".jpg"  # Default to .jpg if no extension
    
    # Create SEO-friendly components
    components = []
    
    # Add prefix if provided
    if prefix:
        components.append(prefix)
    
    # Add name if provided, cleaned up for URL
    if name:
        # Convert to lowercase and replace spaces with hyphens
        clean_name = name.lower().replace(' ', '-')
        # Remove any non-alphanumeric characters except hyphens
        clean_name = re.sub(r'[^a-z0-9-]', '', clean_name)
        # Replace multiple hyphens with a single hyphen
        clean_name = re.sub(r'-+', '-', clean_name)
        # Remove leading and trailing hyphens
        clean_name = clean_name.strip('-')
        
        # Limit the length of the name
        if len(clean_name) > 50:
            clean_name = clean_name[:50]
        
        components.append(clean_name)
    
    # Join components with hyphens
    result = "-".join(components)
    
    # Add the file extension
    result += ext
    
    return result

def download_and_optimize_image(url, output_path):
    """Download and optimize an image using proxy rotation."""
    global proxy_manager
    
    # Set up headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    max_retries = 3
    retry_count = 0
    timeout = 30  # Default timeout
    
    if proxy_manager and proxy_manager.use_proxies:
        timeout = 60  # Longer timeout for proxy connections
    
    while retry_count < max_retries:
        try:
            current_proxy = {}
            current_proxy_url = None
            
            if proxy_manager and proxy_manager.use_proxies:
                current_proxy = proxy_manager.get_proxy()
                # Extract the proxy URL for tracking
                if current_proxy:
                    if 'http' in current_proxy:
                        current_proxy_url = current_proxy['http']
                    elif 'https' in current_proxy:
                        current_proxy_url = current_proxy['https']
                    
                    print(f"Using proxy: {current_proxy_url} for image: {url}")
                    # Debug information to verify proxy is being used
                    if OXYLABS_ENDPOINT in str(current_proxy_url):
                        print(f"DEBUG: Using Oxylabs proxy for {url}")
                        print(f"DEBUG: Proxy config: {current_proxy}")
                else:
                    if not proxy_manager.force_own_ip:
                        print(f"ERROR: No proxy available for {url} and force_own_ip is not enabled.")
                        print("Skipping this image to avoid using your own IP.")
                        return False
                    print(f"No proxy available, using direct connection for image: {url}")
            elif not proxy_manager or not proxy_manager.force_own_ip:
                print(f"ERROR: Proxy usage is disabled for {url} and force_own_ip is not enabled.")
                print("Skipping this image to avoid using your own IP.")
                return False
            
            # Make the request with proxies
            print(f"Making request to {url}...")
            start_time = time.time()
            response = requests.get(url, headers=headers, proxies=current_proxy, timeout=timeout)
            end_time = time.time()
            print(f"Request completed in {end_time - start_time:.2f} seconds")
            
            response.raise_for_status()
            
            # Print response headers to verify proxy usage
            if current_proxy:
                print(f"DEBUG: Response headers: {dict(response.headers)}")
                if 'Via' in response.headers:
                    print(f"DEBUG: Response 'Via' header: {response.headers.get('Via')}")
            
            # Open the image
            img = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize if too large
            max_size = 1200
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Save with optimized quality
            img.save(output_path, 'JPEG', quality=85, optimize=True)
            
            # Mark proxy as successful if used
            if current_proxy_url and proxy_manager:
                proxy_manager.mark_proxy_success(current_proxy_url)
                print(f"Successfully used proxy {current_proxy_url} for {url}")
                
            return True
            
        except requests.exceptions.ProxyError as e:
            print(f"Proxy error for image {url}: {e}")
            print(f"Proxy error details: {str(e.__cause__)}")
            
            # Mark proxy as failed if used
            if current_proxy_url and proxy_manager:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for image {url}: {e}")
            
            # Mark proxy as failed if used
            if current_proxy_url and proxy_manager:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Request error for image {url}: {e}")
            
            # Mark proxy as failed if used
            if current_proxy_url and proxy_manager:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except Exception as e:
            print(f"Error downloading/optimizing image {url}: {str(e)}")
            retry_count += 1
        
        # Wait before retrying
        if retry_count < max_retries:
            time.sleep(2 * retry_count)  # Exponential backoff
    
    return False

def upload_to_cloudflare_r2(file_path, object_key):
    """Upload a file to Cloudflare R2."""
    try:
        # Check if boto3 is available
        try:
            import boto3
        except ImportError:
            print("boto3 is not installed. Skipping upload to Cloudflare R2.")
            print("To install boto3, run: pip install boto3")
            return None
        
        # Check if Cloudflare credentials are available
        if not CLOUDFLARE_ACCESS_KEY_ID or not CLOUDFLARE_SECRET_ACCESS_KEY or not CLOUDFLARE_ENDPOINT:
            print("Cloudflare R2 credentials not set. Skipping upload.")
            print(f"CLOUDFLARE_ACCESS_KEY_ID: {'Available' if CLOUDFLARE_ACCESS_KEY_ID else 'Missing'}")
            print(f"CLOUDFLARE_SECRET_ACCESS_KEY: {'Available' if CLOUDFLARE_SECRET_ACCESS_KEY else 'Missing'}")
            print(f"CLOUDFLARE_ENDPOINT: {'Available' if CLOUDFLARE_ENDPOINT else 'Missing'}")
            return None
        
        print(f"Uploading {file_path} to Cloudflare R2 as {object_key}...")
        
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url=CLOUDFLARE_ENDPOINT,
            aws_access_key_id=CLOUDFLARE_ACCESS_KEY_ID,
            aws_secret_access_key=CLOUDFLARE_SECRET_ACCESS_KEY
        )
        
        # Upload file
        s3.upload_file(
            file_path, 
            CLOUDFLARE_R2_BUCKET_NAME, 
            object_key,
            ExtraArgs={
                'ContentType': 'image/jpeg',
                'CacheControl': 'public, max-age=31536000'
            }
        )
        
        # Return the public URL
        return f"{CLOUDFLARE_PUBLIC_URL}/{object_key}"
    except Exception as e:
        print(f"Error uploading to Cloudflare R2: {str(e)}")
        return None

def process_image_urls(limit=None, minifigs_only=False, start_index=0, batch_size=0, dry_run=False):
    """
    Process image URLs from the catalog data.
    
    Args:
        limit: Maximum number of images to process
        minifigs_only: Only process minifigure images
        start_index: Start index for batch processing
        batch_size: Batch size for processing
        dry_run: If True, skip downloading images but update mappings
    
    Returns:
        Tuple of (successful_count, failed_count)
    """
    print("Processing image URLs in catalog data...")
    
    # Load existing image mapping if it exists
    image_mapping = {}
    if os.path.exists(IMAGE_MAPPING_FILE):
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    
    # Create a reverse mapping for quick lookup
    reverse_mapping = {v: k for k, v in image_mapping.items()}
    
    # Get image URLs from sets.csv
    sets_urls = []
    if not minifigs_only:
        with open(os.path.join(EXTRACTED_DIR, "sets.csv"), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'img_url' in row and is_valid_image_url(row['img_url']):
                    # Skip if the URL is already a Cloudflare URL
                    if "images.bricksdeal.com" in row['img_url']:
                        continue
                    sets_urls.append({
                        'url': row['img_url'],
                        'set_num': row['set_num'],
                        'name': row['name'],
                        'theme_id': row['theme_id']
                    })
    
    # Get image URLs from minifigs.csv
    minifigs_urls = []
    with open(os.path.join(EXTRACTED_DIR, "minifigs.csv"), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'img_url' in row and is_valid_image_url(row['img_url']):
                # Skip if the URL is already a Cloudflare URL
                if "images.bricksdeal.com" in row['img_url']:
                    continue
                minifigs_urls.append({
                    'url': row['img_url'],
                    'fig_num': row['fig_num'],
                    'name': row['name']
                })
    
    # Combine URLs
    all_urls = []
    if not minifigs_only:
        all_urls.extend([{'url': item['url'], 'type': 'set', 'data': item} for item in sets_urls])
    all_urls.extend([{'url': item['url'], 'type': 'minifig', 'data': item} for item in minifigs_urls])
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        all_urls = all_urls[:limit]
    
    # Apply batch processing if specified
    if batch_size > 0:
        end_index = start_index + batch_size
        all_urls = all_urls[start_index:end_index]
    
    print(f"Found {len(all_urls)} items with images to process")
    
    # Process images
    successful = 0
    failed = 0
    skipped = 0
    failed_downloads = []
    
    for i, item in enumerate(all_urls):
        url = item['url']
        item_type = item['type']
        data = item['data']
        
        # Skip if already in mapping
        if url in image_mapping:
            print(f"Image already processed: {url} -> {image_mapping[url]}")
            successful += 1
            skipped += 1
            continue
        
        # Create filename
        if item_type == 'set':
            set_num = data['set_num']
            name = data['name']
            theme_id = data['theme_id']
            theme_name = get_theme_name(theme_id)
            filename = create_seo_friendly_filename(url, prefix=f"lego-{theme_name}-", name=name)
        else:  # minifig
            fig_num = data['fig_num']
            name = data['name']
            filename = create_seo_friendly_filename(url, prefix="lego-minifig-", name=name)
        
        output_path = os.path.join(IMAGES_DIR, filename)
        
        # Check if the file already exists
        file_exists = os.path.exists(output_path)
        
        if dry_run:
            if file_exists:
                print(f"DRY RUN: Image already exists at {output_path}")
            else:
                print(f"DRY RUN: Would download {url} to {output_path}")
            
            # Create Cloudflare URL for mapping
            if item_type == 'set':
                object_key = f"catalog/set/{filename}"
            else:  # minifig
                object_key = f"catalog/minifig/{filename}"
            
            cloudflare_url = f"{CLOUDFLARE_PUBLIC_URL}/{object_key}"
            
            # Add to mapping
            image_mapping[url] = cloudflare_url
            print(f"DRY RUN: Added mapping: {url} -> {cloudflare_url}")
            successful += 1
            continue
        
        # If not dry run, proceed with download and upload
        if file_exists:
            print(f"Image already exists at {output_path}, skipping download")
            success = True
        else:
            # Download and optimize image
            success = download_and_optimize_image(url, output_path)
        
        if success:
            # Upload to Cloudflare R2
            if item_type == 'set':
                object_key = f"catalog/set/{filename}"
            else:  # minifig
                object_key = f"catalog/minifig/{filename}"
            
            cloudflare_url = upload_to_cloudflare_r2(output_path, object_key)
            
            if cloudflare_url:
                # Add to mapping
                image_mapping[url] = cloudflare_url
                print(f"Processed image: {url} -> {cloudflare_url}")
                successful += 1
            else:
                print(f"Failed to upload image to Cloudflare R2: {url}")
                failed += 1
                failed_downloads.append({"url": url, "reason": "Failed to upload to Cloudflare R2"})
        else:
            print(f"Failed to download/process image: {url}")
            failed += 1
            failed_downloads.append({"url": url, "reason": "Failed to download/process"})
    
    # Save failed downloads
    if failed_downloads:
        failed_downloads_file = os.path.join(IMAGES_DIR, "failed_downloads.json")
        
        # Load existing failed downloads if the file exists
        existing_failed = []
        if os.path.exists(failed_downloads_file):
            with open(failed_downloads_file, 'r') as f:
                try:
                    existing_failed = json.load(f)
                except json.JSONDecodeError:
                    existing_failed = []
        
        # Add new failed downloads
        existing_failed.extend(failed_downloads)
        
        # Save updated failed downloads
        with open(failed_downloads_file, 'w') as f:
            json.dump(existing_failed, f, indent=2)
        
        print(f"Saved {len(failed_downloads)} failed downloads to {failed_downloads_file}")
    
    # Save image mapping
    with open(IMAGE_MAPPING_FILE, 'w') as f:
        json.dump(image_mapping, f, indent=2)
    
    print(f"Processed {len(image_mapping)} images. Mapping saved to {IMAGE_MAPPING_FILE}")
    if skipped > 0:
        print(f"Skipped {skipped} already processed images")
    
    return successful, failed

def get_theme_name(theme_id):
    """Get the theme name from the theme ID."""
    if not theme_id:
        return ""
    
    themes_csv = os.path.join(EXTRACTED_DIR, "themes.csv")
    if not os.path.exists(themes_csv):
        return ""
    
    try:
        with open(themes_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('id') == theme_id:
                    return row.get('name', '')
    except Exception as e:
        print(f"Error reading themes.csv: {str(e)}")
    
    return ""

def update_csv_with_new_urls():
    """Update CSV files with new image URLs."""
    print("Updating CSV files with new image URLs...")
    
    # Load image mapping
    if not os.path.exists(IMAGE_MAPPING_FILE):
        print(f"Image mapping file not found: {IMAGE_MAPPING_FILE}")
        return
    
    with open(IMAGE_MAPPING_FILE, 'r') as f:
        image_mapping = json.load(f)
    
    # Update sets.csv
    sets_csv = os.path.join(EXTRACTED_DIR, "sets.csv")
    if os.path.exists(sets_csv):
        # Create a temporary file
        temp_csv = os.path.join(EXTRACTED_DIR, "sets_updated.csv")
        
        # Read and update the CSV
        updated_count = 0
        with open(sets_csv, 'r', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            with open(temp_csv, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    img_url = row.get('img_url', '')
                    if img_url in image_mapping:
                        row['img_url'] = image_mapping[img_url]
                        updated_count += 1
                    
                    writer.writerow(row)
        
        # Replace the original file
        os.replace(temp_csv, sets_csv)
        
        print(f"Updated {updated_count} image URLs in sets.csv")
    
    # Update minifigs.csv
    minifigs_csv = os.path.join(EXTRACTED_DIR, "minifigs.csv")
    if os.path.exists(minifigs_csv):
        # Create a temporary file
        temp_csv = os.path.join(EXTRACTED_DIR, "minifigs_updated.csv")
        
        # Read and update the CSV
        updated_count = 0
        with open(minifigs_csv, 'r', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            with open(temp_csv, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    img_url = row.get('img_url', '')
                    if img_url in image_mapping:
                        row['img_url'] = image_mapping[img_url]
                        updated_count += 1
                    
                    writer.writerow(row)
        
        # Replace the original file
        os.replace(temp_csv, minifigs_csv)
        
        print(f"Updated {updated_count} image URLs in minifigs.csv")

def test_multiple_images():
    """Test function to demonstrate how the script handles multiple images for the same set."""
    print("Testing multiple images for the same set...")
    
    # Load existing image mapping
    image_mapping = {}
    if os.path.exists(IMAGE_MAPPING_FILE):
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    
    # Track processed item IDs to handle multiple images for the same item
    processed_item_ids = {}
    for url, mapped_url in image_mapping.items():
        # Extract item ID from the mapped URL
        if '/set/' in mapped_url:
            # Extract set number from the end of the URL
            match = re.search(r'-([^-]+)(?:-alt|-back|-side|-view\d+)?\.jpg$', mapped_url)
            if match:
                item_id = match.group(1)
                processed_item_ids[item_id] = processed_item_ids.get(item_id, 0) + 1
        elif '/minifig/' in mapped_url:
            # Extract fig number from the end of the URL
            match = re.search(r'-(fig-\d+)(?:-alt|-back|-side|-view\d+)?\.jpg$', mapped_url)
            if match:
                item_id = match.group(1)
                processed_item_ids[item_id] = processed_item_ids.get(item_id, 0) + 1
    
    # Print the count of images for each item
    print("Current image counts:")
    for item_id, count in processed_item_ids.items():
        print(f"  {item_id}: {count} images")
    
    # Example sets to demonstrate naming patterns
    examples = [
        {
            "item_id": "75192-1",
            "item_type": "set",
            "item_name": "Millennium Falcon",
            "theme_name": "Star Wars"
        },
        {
            "item_id": "fig-000123",
            "item_type": "minifig",
            "item_name": "Darth Vader",
            "theme_name": ""
        }
    ]
    
    print("\nExample naming patterns for multiple images:")
    
    for example in examples:
        item_id = example["item_id"]
        item_type = example["item_type"]
        item_name = example["item_name"]
        theme_name = example["theme_name"]
        
        print(f"\n{item_type.upper()}: {item_name} ({item_id})")
        
        # Generate filenames for up to 6 images
        for i in range(6):
            # Create SEO-friendly filename
            if item_type == 'set':
                # Format: lego-[theme]-[set-name]-[set-number]-[view].jpg
                theme_part = f"{theme_name.lower()}-" if theme_name else ""
                
                # Add view suffix if this is not the first image
                view_suffix = ""
                if i > 0:
                    # Use descriptive suffixes for the first few images
                    if i == 1:
                        view_suffix = "-alt"
                    elif i == 2:
                        view_suffix = "-back"
                    elif i == 3:
                        view_suffix = "-side"
                    else:
                        # For more images, use a numeric suffix
                        view_suffix = f"-view{i}"
                
                filename = f"lego-{theme_part}{item_name.lower()}-{item_id}{view_suffix}"
                
                # Clean up the filename
                filename = re.sub(r'[^a-zA-Z0-9-]', '-', filename)
                filename = re.sub(r'-+', '-', filename)
                filename = filename.strip('-')
                
                # Add extension
                filename = f"{filename}.jpg"
            else:  # minifig
                # Format: lego-minifig-[name]-[fig-number]-[view].jpg
                clean_name = re.sub(r'[^a-zA-Z0-9]', '-', item_name)
                clean_name = re.sub(r'-+', '-', clean_name)
                clean_name = clean_name.strip('-').lower()
                
                # Add view suffix if this is not the first image
                view_suffix = ""
                if i > 0:
                    # Use descriptive suffixes for the first few images
                    if i == 1:
                        view_suffix = "-alt"
                    elif i == 2:
                        view_suffix = "-back"
                    elif i == 3:
                        view_suffix = "-side"
                    else:
                        # For more images, use a numeric suffix
                        view_suffix = f"-view{i}"
                
                filename = f"lego-minifig-{clean_name}-{item_id}{view_suffix}.jpg"
            
            print(f"  Image #{i+1}: {filename}")

def rebuild_image_mapping(force_upload=False):
    """
    Rebuild the image mapping by scanning the catalog-images directory.
    This is useful when there are images in the directory that are not in the mapping file.
    
    Args:
        force_upload (bool): If True, upload all images to Cloudflare R2 even if they're already mapped.
    """
    print("Rebuilding image mapping from catalog-images directory...")
    
    # Ensure the directory exists
    if not os.path.exists(IMAGES_DIR):
        print(f"Images directory not found: {IMAGES_DIR}")
        return
    
    # Load existing image mapping if it exists
    image_mapping = {}
    if os.path.exists(IMAGE_MAPPING_FILE):
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    
    # Get all image files in the directory
    image_files = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg') and os.path.isfile(os.path.join(IMAGES_DIR, f))]
    print(f"Found {len(image_files)} image files in {IMAGES_DIR}")
    
    # Reverse mapping to find original URLs
    reverse_mapping = {v: k for k, v in image_mapping.items()}
    
    # Count of new mappings added
    new_mappings = 0
    uploaded_images = 0
    skipped_images = 0
    
    # Process each image file
    for i, image_file in enumerate(image_files):
        # Show progress every 100 files
        if i % 100 == 0:
            print(f"Processing file {i+1}/{len(image_files)}...")
        
        # Create the Cloudflare URL
        if 'minifig' in image_file.lower() or 'fig-' in image_file.lower():
            # This is a minifig image
            r2_object_key = f"catalog/minifig/{image_file}"
            item_type = 'minifig'
        else:
            # This is a set image
            r2_object_key = f"catalog/set/{image_file}"
            item_type = 'set'
        
        cloudflare_url = f"{CLOUDFLARE_PUBLIC_URL}/{r2_object_key}"
        local_path = os.path.join(IMAGES_DIR, image_file)
        
        # Check if this URL is already in the reverse mapping
        if cloudflare_url in reverse_mapping and not force_upload:
            # Already mapped, skip
            skipped_images += 1
            continue
        
        # Upload to Cloudflare R2 if force_upload is True
        if force_upload:
            print(f"Uploading {image_file} to Cloudflare R2...")
            cloudflare_url = upload_to_cloudflare_r2(local_path, r2_object_key)
            if cloudflare_url:
                uploaded_images += 1
        
        # Try to extract the set/fig number from the filename using different patterns
        if item_type == 'set':
            # Try different patterns to extract the set number
            patterns = [
                r'-(\d+[a-zA-Z0-9-]+)(?:-alt|-back|-side|-view\d+)?\.jpg$',  # Extract number at the end
                r'lego-[^-]+-([^-]+)-[^-]+\.jpg$',  # Three-part pattern, middle part
                r'lego-[^-]+-([^-]+)\.jpg$',  # Two-part pattern, last part
                r'([0-9]+(?:-[0-9]+)?)(?:-alt|-back|-side|-view\d+)?\.jpg$',  # Just numbers with optional dash
                r'([a-zA-Z0-9-]+)\.jpg$',  # Any alphanumeric before .jpg
            ]
            
            set_num = None
            for pattern in patterns:
                match = re.search(pattern, image_file)
                if match:
                    # Use the matched group as the set number
                    set_num = match.group(1)
                    break
            
            if set_num:
                # Try different variations of the original URL
                original_urls = [
                    f"https://cdn.rebrickable.com/media/sets/{set_num}.jpg",
                    f"https://cdn.rebrickable.com/media/sets/{set_num}-1.jpg",
                    f"https://cdn.rebrickable.com/media/sets/{set_num}-2.jpg",
                ]
                
                # Add to mapping if not already present
                for original_url in original_urls:
                    if original_url not in image_mapping and cloudflare_url not in reverse_mapping.keys():
                        image_mapping[original_url] = cloudflare_url
                        reverse_mapping[cloudflare_url] = original_url
                        new_mappings += 1
                        if new_mappings % 10 == 0:
                            print(f"Added {new_mappings} new mappings so far...")
                        break
            else:
                # If no pattern matched, use a generic mapping based on the filename
                generic_set_id = image_file.replace('.jpg', '')
                original_url = f"https://cdn.rebrickable.com/media/sets/{generic_set_id}.jpg"
                if original_url not in image_mapping and cloudflare_url not in reverse_mapping.keys():
                    image_mapping[original_url] = cloudflare_url
                    reverse_mapping[cloudflare_url] = original_url
                    new_mappings += 1
                    if new_mappings % 10 == 0:
                        print(f"Added {new_mappings} new mappings so far...")
        else:  # minifig
            # Try different patterns to extract the fig number
            patterns = [
                r'-(fig-\d+)(?:-alt|-back|-side|-view\d+)?\.jpg$',  # Standard pattern
                r'lego-minifig-([^-]+)-([^-]+)\.jpg$',  # Two-part pattern
                r'fig-(\d+)(?:-alt|-back|-side|-view\d+)?\.jpg$',  # Just fig number
                r'([a-zA-Z0-9-]+)\.jpg$',  # Any alphanumeric before .jpg
            ]
            
            fig_num = None
            for pattern in patterns:
                match = re.search(pattern, image_file)
                if match:
                    # Use the matched group as the fig number
                    fig_num = match.group(1)
                    break
            
            if fig_num:
                # Try different variations of the original URL
                original_urls = [
                    f"https://cdn.rebrickable.com/media/sets/{fig_num}.jpg",
                    f"https://cdn.rebrickable.com/media/sets/{fig_num}-1.jpg",
                    f"https://cdn.rebrickable.com/media/sets/fig-{fig_num.replace('fig-', '')}.jpg",
                ]
                
                # Add to mapping if not already present
                for original_url in original_urls:
                    if original_url not in image_mapping and cloudflare_url not in reverse_mapping.keys():
                        image_mapping[original_url] = cloudflare_url
                        reverse_mapping[cloudflare_url] = original_url
                        new_mappings += 1
                        if new_mappings % 10 == 0:
                            print(f"Added {new_mappings} new mappings so far...")
                        break
            else:
                # If no pattern matched, use a generic mapping based on the filename
                generic_fig_id = image_file.replace('.jpg', '')
                original_url = f"https://cdn.rebrickable.com/media/sets/{generic_fig_id}.jpg"
                if original_url not in image_mapping and cloudflare_url not in reverse_mapping.keys():
                    image_mapping[original_url] = cloudflare_url
                    reverse_mapping[cloudflare_url] = original_url
                    new_mappings += 1
                    if new_mappings % 10 == 0:
                        print(f"Added {new_mappings} new mappings so far...")
    
    # Save updated image mapping
    with open(IMAGE_MAPPING_FILE, 'w') as f:
        json.dump(image_mapping, f, indent=2)
    
    print(f"Added {new_mappings} new mappings to image_mapping.json")
    print(f"Skipped {skipped_images} already mapped images")
    if force_upload:
        print(f"Uploaded {uploaded_images} images to Cloudflare R2")
    print(f"Total mappings: {len(image_mapping)}")
    
    # Update CSV files with the new image URLs
    update_csv_with_new_urls()
    
    return new_mappings

def test_proxy():
    """Test the proxy configuration by making a request to a test URL."""
    print("Testing proxy configuration...")
    
    # Initialize proxy manager with proxies enabled
    global proxy_manager
    test_proxy_manager = proxy_manager
    
    if not test_proxy_manager.proxies:
        print("No proxies available for testing.")
        if not test_proxy_manager.force_own_ip:
            print("Since force_own_ip is not enabled, no direct connections will be allowed.")
            return False
        else:
            print("Direct connections will be used as fallback since force_own_ip is enabled.")
    
    # Test URL that returns IP information - use Oxylabs' own test URL
    test_url = "http://ip.oxylabs.io"
    
    # Set up headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    # Try each proxy
    for proxy_url in test_proxy_manager.proxies:
        print(f"\nTesting proxy: {proxy_url}")
        
        # Get proxy configuration
        current_proxy = {}
        if proxy_url.startswith(('http://', 'https://')):
            scheme = proxy_url.split('://')[0]
            if OXYLABS_ENDPOINT in proxy_url:
                # For Oxylabs, set both http and https
                current_proxy = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            else:
                current_proxy = {scheme: proxy_url}
        else:
            current_proxy = {'http': f'http://{proxy_url}', 'https': f'https://{proxy_url}'}
        
        print(f"Proxy configuration: {current_proxy}")
        
        try:
            # Make request with proxy
            print(f"Making request to {test_url}...")
            response = requests.get(test_url, headers=headers, proxies=current_proxy, timeout=20)
            response.raise_for_status()
            
            # Print response
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            # Check if the IP is different from the local IP
            if "84.83.5.229" not in response.text:
                print(f"✅ Proxy test successful for {proxy_url} - Using proxy IP: {response.text.strip()}")
                test_proxy_manager.mark_proxy_success(proxy_url)
            else:
                print(f"❌ Proxy test failed for {proxy_url} - Still using local IP: {response.text.strip()}")
                test_proxy_manager.mark_proxy_failure(proxy_url)
            
        except Exception as e:
            print(f"❌ Proxy test failed for {proxy_url}: {str(e)}")
            test_proxy_manager.mark_proxy_failure(proxy_url)
    
    # Test direct connection if force_own_ip is enabled
    if test_proxy_manager.force_own_ip:
        print("\nTesting direct connection (force_own_ip is enabled):")
        try:
            # Make request without proxy
            print(f"Making request to {test_url} without proxy...")
            response = requests.get(test_url, headers=headers, timeout=20)
            response.raise_for_status()
            
            # Print response
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            print(f"✅ Direct connection test successful - Using IP: {response.text.strip()}")
        except Exception as e:
            print(f"❌ Direct connection test failed: {str(e)}")
    
    # Summary
    print("\nProxy Test Summary:")
    print(f"Total proxies tested: {len(test_proxy_manager.proxies)}")
    print(f"Working proxies: {len(test_proxy_manager.working_proxies)}")
    print(f"Failed proxies: {len(test_proxy_manager.failed_proxies)}")
    
    if test_proxy_manager.working_proxies:
        print("\n✅ At least one proxy is working correctly.")
        return True
    elif test_proxy_manager.force_own_ip:
        print("\n⚠️ No working proxies found, but direct connections are allowed.")
        return True
    else:
        print("\n❌ No working proxies found and direct connections are not allowed.")
        print("Use --force-own-ip if you want to allow direct connections.")
        return False

def validate_image_urls(only_cloudflare=True):
    """
    Validate image URLs in the image mapping to check if they are accessible.
    
    Args:
        only_cloudflare (bool): If True, only validate URLs from Cloudflare (images.bricksdeal.com)
    
    Returns:
        Tuple of (valid_count, invalid_count, validation_results)
    """
    print("Validating image URLs...")
    
    # Load image mapping
    if not os.path.exists(IMAGE_MAPPING_FILE):
        print(f"Image mapping file not found: {IMAGE_MAPPING_FILE}")
        return 0, 0, []
    
    with open(IMAGE_MAPPING_FILE, 'r') as f:
        image_mapping = json.load(f)
    
    print(f"Found {len(image_mapping)} image mappings to validate")
    
    # Set up headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    # Validate URLs
    valid_count = 0
    invalid_count = 0
    validation_results = []
    
    for original_url, cloudflare_url in image_mapping.items():
        # Skip if not a Cloudflare URL and only_cloudflare is True
        if only_cloudflare and "images.bricksdeal.com" not in cloudflare_url:
            continue
        
        print(f"Validating: {cloudflare_url}")
        
        try:
            # Make a HEAD request to check if the URL is accessible
            response = requests.head(cloudflare_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Valid URL: {cloudflare_url}")
                valid_count += 1
                validation_results.append({
                    "original_url": original_url,
                    "cloudflare_url": cloudflare_url,
                    "status": "valid",
                    "status_code": response.status_code
                })
            else:
                print(f"❌ Invalid URL: {cloudflare_url} (Status code: {response.status_code})")
                invalid_count += 1
                validation_results.append({
                    "original_url": original_url,
                    "cloudflare_url": cloudflare_url,
                    "status": "invalid",
                    "status_code": response.status_code
                })
        except Exception as e:
            print(f"❌ Error validating URL: {cloudflare_url} ({str(e)})")
            invalid_count += 1
            validation_results.append({
                "original_url": original_url,
                "cloudflare_url": cloudflare_url,
                "status": "error",
                "error": str(e)
            })
    
    # Save validation results
    validation_file = os.path.join(IMAGES_DIR, "validation_results.json")
    with open(validation_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    print(f"Validation complete: {valid_count} valid URLs, {invalid_count} invalid URLs")
    print(f"Results saved to {validation_file}")
    
    return valid_count, invalid_count, validation_results

def list_r2_objects():
    """
    List all objects in the Cloudflare R2 bucket and verify they're mapped in the CSV files.
    Returns a list of all object keys in the bucket.
    """
    print("Listing objects in Cloudflare R2 bucket...")
    
    # Check if environment variables are set
    endpoint = os.environ.get('CLOUDFLARE_R2_ENDPOINT')
    access_key = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID')
    secret_key = os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
    
    if not all([endpoint, access_key, secret_key]):
        print("Error: Cloudflare R2 environment variables are not set correctly.")
        print("Please ensure the following environment variables are set:")
        print("  - CLOUDFLARE_R2_ENDPOINT")
        print("  - CLOUDFLARE_R2_ACCESS_KEY_ID")
        print("  - CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        return []
    
    try:
        # Initialize S3 client for Cloudflare R2
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # List all objects in the bucket
        all_objects = []
        continuation_token = None
        
        while True:
            try:
                if continuation_token:
                    response = s3.list_objects_v2(
                        Bucket=CLOUDFLARE_R2_BUCKET_NAME,
                        ContinuationToken=continuation_token
                    )
                else:
                    response = s3.list_objects_v2(
                        Bucket=CLOUDFLARE_R2_BUCKET_NAME
                    )
                
                if 'Contents' in response:
                    all_objects.extend(response['Contents'])
                
                if not response.get('IsTruncated'):
                    break
                
                continuation_token = response.get('NextContinuationToken')
            except Exception as e:
                print(f"Error listing objects: {str(e)}")
                break
        
        print(f"Found {len(all_objects)} objects in R2 bucket")
        return all_objects
    except Exception as e:
        print(f"Error connecting to Cloudflare R2: {str(e)}")
        return []

def verify_r2_mappings(cleanup_local=False):
    """
    Verify that all objects in the R2 bucket are mapped in the CSV files.
    
    Args:
        cleanup_local (bool): If True, remove local files that have been successfully uploaded to R2
        
    Returns:
        Tuple of (mapped_count, unmapped_count, removed_count)
    """
    print("Verifying R2 bucket mappings...")
    
    # Get all objects in the R2 bucket
    r2_objects = list_r2_objects()
    
    if not r2_objects:
        print("No objects found in R2 bucket or error connecting to R2.")
        return 0, 0, 0
    
    # Create a set of all R2 object keys
    r2_object_keys = {obj['Key'] for obj in r2_objects}
    
    # Load image mapping
    if not os.path.exists(IMAGE_MAPPING_FILE):
        print(f"Image mapping file not found: {IMAGE_MAPPING_FILE}")
        return 0, len(r2_object_keys), 0
    
    try:
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    except Exception as e:
        print(f"Error loading image mapping file: {str(e)}")
        return 0, len(r2_object_keys), 0
    
    # Create a set of all Cloudflare URLs in the mapping
    cloudflare_urls = set(image_mapping.values())
    
    # Convert Cloudflare URLs to object keys
    mapped_object_keys = set()
    for url in cloudflare_urls:
        if url and isinstance(url, str) and url.startswith(CLOUDFLARE_PUBLIC_URL):
            object_key = url.replace(CLOUDFLARE_PUBLIC_URL + "/", "")
            mapped_object_keys.add(object_key)
    
    # Find unmapped objects
    unmapped_object_keys = r2_object_keys - mapped_object_keys
    
    print(f"Total R2 objects: {len(r2_object_keys)}")
    print(f"Mapped objects: {len(mapped_object_keys)}")
    print(f"Unmapped objects: {len(unmapped_object_keys)}")
    
    # Check if the mapped objects are in the CSV files
    sets_csv = os.path.join(EXTRACTED_DIR, "sets.csv")
    minifigs_csv = os.path.join(EXTRACTED_DIR, "minifigs.csv")
    
    csv_urls = set()
    
    # Check sets.csv
    if os.path.exists(sets_csv):
        try:
            with open(sets_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'img_url' in row and row['img_url'] and isinstance(row['img_url'], str) and row['img_url'].startswith(CLOUDFLARE_PUBLIC_URL):
                        csv_urls.add(row['img_url'])
        except Exception as e:
            print(f"Error reading sets.csv: {str(e)}")
    
    # Check minifigs.csv
    if os.path.exists(minifigs_csv):
        try:
            with open(minifigs_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'img_url' in row and row['img_url'] and isinstance(row['img_url'], str) and row['img_url'].startswith(CLOUDFLARE_PUBLIC_URL):
                        csv_urls.add(row['img_url'])
        except Exception as e:
            print(f"Error reading minifigs.csv: {str(e)}")
    
    # Convert CSV URLs to object keys
    csv_object_keys = set()
    for url in csv_urls:
        if url and isinstance(url, str) and url.startswith(CLOUDFLARE_PUBLIC_URL):
            object_key = url.replace(CLOUDFLARE_PUBLIC_URL + "/", "")
            csv_object_keys.add(object_key)
    
    # Find objects that are mapped but not in the CSV files
    not_in_csv = mapped_object_keys - csv_object_keys
    
    print(f"URLs in CSV files: {len(csv_urls)}")
    print(f"Objects in CSV files: {len(csv_object_keys)}")
    print(f"Mapped objects not in CSV files: {len(not_in_csv)}")
    
    # If requested, clean up local files that have been uploaded to R2
    removed_count = 0
    if cleanup_local:
        print("Cleaning up local files that have been uploaded to R2...")
        
        # Get all local image files
        try:
            local_files = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg') and os.path.isfile(os.path.join(IMAGES_DIR, f))]
            print(f"Found {len(local_files)} local image files")
            
            # For each local file, check if it's been uploaded to R2 and is in the CSV files
            for local_file in local_files:
                # Determine the R2 object key for this file
                if 'minifig' in local_file.lower() or 'fig-' in local_file.lower():
                    object_key = f"catalog/minifig/{local_file}"
                else:
                    object_key = f"catalog/set/{local_file}"
                
                # If the object is in R2 and in the CSV files, we can safely remove the local file
                if object_key in r2_object_keys and object_key in csv_object_keys:
                    try:
                        os.remove(os.path.join(IMAGES_DIR, local_file))
                        removed_count += 1
                        if removed_count % 100 == 0:
                            print(f"Removed {removed_count} local files so far...")
                    except Exception as e:
                        print(f"Error removing file {local_file}: {str(e)}")
            
            print(f"Removed {removed_count} local files that were successfully uploaded to R2 and mapped in CSV files")
        except Exception as e:
            print(f"Error listing local files: {str(e)}")
    
    return len(mapped_object_keys), len(unmapped_object_keys), removed_count

def cleanup_local_files():
    """
    Clean up local files that have been uploaded to Cloudflare R2 based on the image mapping.
    This function doesn't require direct access to the R2 bucket, it just uses the image mapping.
    
    Returns:
        int: Number of files removed
    """
    print("Cleaning up local files based on image mapping...")
    
    # Load image mapping
    if not os.path.exists(IMAGE_MAPPING_FILE):
        print(f"Image mapping file not found: {IMAGE_MAPPING_FILE}")
        return 0
    
    try:
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    except Exception as e:
        print(f"Error loading image mapping file: {str(e)}")
        return 0
    
    # Create a set of all Cloudflare URLs in the mapping
    cloudflare_urls = set(image_mapping.values())
    
    # Check if the mapped objects are in the CSV files
    sets_csv = os.path.join(EXTRACTED_DIR, "sets.csv")
    minifigs_csv = os.path.join(EXTRACTED_DIR, "minifigs.csv")
    
    csv_urls = set()
    
    # Check sets.csv
    if os.path.exists(sets_csv):
        try:
            with open(sets_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'img_url' in row and row['img_url'] and isinstance(row['img_url'], str) and row['img_url'].startswith(CLOUDFLARE_PUBLIC_URL):
                        csv_urls.add(row['img_url'])
        except Exception as e:
            print(f"Error reading sets.csv: {str(e)}")
    
    # Check minifigs.csv
    if os.path.exists(minifigs_csv):
        try:
            with open(minifigs_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'img_url' in row and row['img_url'] and isinstance(row['img_url'], str) and row['img_url'].startswith(CLOUDFLARE_PUBLIC_URL):
                        csv_urls.add(row['img_url'])
        except Exception as e:
            print(f"Error reading minifigs.csv: {str(e)}")
    
    # Get all local image files
    try:
        local_files = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.jpg') and os.path.isfile(os.path.join(IMAGES_DIR, f))]
        print(f"Found {len(local_files)} local image files")
        
        # For each local file, check if it's mapped and in the CSV files
        removed_count = 0
        for local_file in local_files:
            # Determine the Cloudflare URL for this file
            if 'minifig' in local_file.lower() or 'fig-' in local_file.lower():
                cloudflare_url = f"{CLOUDFLARE_PUBLIC_URL}/catalog/minifig/{local_file}"
            else:
                cloudflare_url = f"{CLOUDFLARE_PUBLIC_URL}/catalog/set/{local_file}"
            
            # If the URL is in the mapping values and in the CSV files, we can safely remove the local file
            if cloudflare_url in cloudflare_urls and cloudflare_url in csv_urls:
                try:
                    os.remove(os.path.join(IMAGES_DIR, local_file))
                    removed_count += 1
                    if removed_count % 100 == 0:
                        print(f"Removed {removed_count} local files so far...")
                except Exception as e:
                    print(f"Error removing file {local_file}: {str(e)}")
        
        print(f"Removed {removed_count} local files that were successfully uploaded to R2 and mapped in CSV files")
        return removed_count
    except Exception as e:
        print(f"Error listing local files: {str(e)}")
        return 0

def main(args=None):
    """Main entry point for the script."""
    if args is None:
        parser = argparse.ArgumentParser(description="Extract catalog data from Rebrickable")
        parser.add_argument("--extract-only", action="store_true", help="Only extract .gz files without processing images")
        parser.add_argument("--process-images", action="store_true", help="Process images without extracting .gz files")
        parser.add_argument("--update-csv", action="store_true", help="Update CSV files with new image URLs")
        parser.add_argument("--limit", type=int, help="Limit the number of images to process")
        parser.add_argument("--minifigs-only", action="store_true", help="Process only minifigure images")
        parser.add_argument("--test", action="store_true", help="Run test function for multiple images")
        parser.add_argument("--use-proxies", action="store_true", help="Use proxy rotation for image downloads")
        parser.add_argument("--proxies-file", type=str, default=PROXIES_FILE, help="File containing proxy URLs")
        parser.add_argument("--start-index", type=int, default=0, help="Start index for batch processing")
        parser.add_argument("--batch-size", type=int, default=0, help="Batch size for processing (0 means process all)")
        parser.add_argument("--rebuild-mapping", action="store_true", help="Rebuild image mapping from catalog-images directory")
        parser.add_argument("--force-upload", action="store_true", help="Force upload all images to Cloudflare R2 when rebuilding mapping")
        parser.add_argument("--test-proxy", action="store_true", help="Test proxy configuration")
        parser.add_argument("--force-own-ip", action="store_true", help="Allow using your own IP address if no proxy is available")
        parser.add_argument("--dry-run", action="store_true", help="Skip downloading images but perform all other operations")
        parser.add_argument("--validate-urls", action="store_true", help="Validate image URLs in the mapping file")
        parser.add_argument("--validate-all", action="store_true", help="Validate all URLs, not just Cloudflare ones")
        parser.add_argument("--verify-r2", action="store_true", help="Verify that all objects in the R2 bucket are mapped in the CSV files")
        parser.add_argument("--cleanup-local", action="store_true", help="Remove local files that have been successfully uploaded to R2")
        
        args = parser.parse_args()
    
    # Initialize the global proxy manager if proxy usage is requested
    global proxy_manager
    proxy_manager = ProxyManager(proxies_file=args.proxies_file, use_proxies=args.use_proxies, force_own_ip=args.force_own_ip)
    
    # Test proxy configuration if requested
    if args.test_proxy:
        test_proxy()
        return
    
    # Run test function if requested
    if args.test:
        test_multiple_images()
        return
    
    # Validate image URLs if requested
    if args.validate_urls:
        validate_image_urls(only_cloudflare=not args.validate_all)
        return
    
    # Rebuild image mapping if requested
    if args.rebuild_mapping:
        rebuild_image_mapping(force_upload=args.force_upload)
        return
    
    # Verify R2 mappings if requested
    if args.verify_r2:
        verify_r2_mappings(cleanup_local=args.cleanup_local)
        return
    
    # Clean up local files if requested
    if args.cleanup_local and not args.verify_r2:
        cleanup_local_files()
        return
    
    # Ensure directories exist
    ensure_directories()
    
    # Extract .gz files if requested or if no specific action is requested
    if args.extract_only or (not args.process_images and not args.update_csv and not args.test and not args.rebuild_mapping and not args.validate_urls and not args.verify_r2 and not args.cleanup_local):
        extract_gz_files()
    
    # Process images if requested or if no specific action is requested
    if args.process_images or (not args.extract_only and not args.update_csv and not args.test and not args.rebuild_mapping and not args.validate_urls and not args.verify_r2 and not args.cleanup_local):
        successful, failed = process_image_urls(
            limit=args.limit, 
            minifigs_only=args.minifigs_only,
            start_index=args.start_index,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        print(f"Summary: {successful} images processed successfully, {failed} images failed")
        
        # Always update CSV files after processing images to ensure URLs are updated
        if not args.update_csv:
            print("Automatically updating CSV files with new image URLs...")
            update_csv_with_new_urls()
    
    # Update CSV files if requested
    if args.update_csv:
        update_csv_with_new_urls()
    
    print("Done!")

if __name__ == "__main__":
    main() 