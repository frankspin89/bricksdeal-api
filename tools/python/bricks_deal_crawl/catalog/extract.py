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
CLOUDFLARE_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET", "lego-images")
CLOUDFLARE_PUBLIC_URL = f"https://{os.environ.get('CLOUDFLARE_DOMAIN', 'images.bricksdeal.com')}"

# Proxy configuration
PROXIES_FILE = os.path.join("input", "proxies.csv")
OXYLABS_USERNAME = os.environ.get("OXYLABS_USERNAME")
OXYLABS_PASSWORD = os.environ.get("OXYLABS_PASSWORD")
OXYLABS_ENDPOINT = os.environ.get("OXYLABS_ENDPOINT", "dc.oxylabs.io")
try:
    OXYLABS_PORTS = [int(port.strip()) for port in os.environ.get("OXYLABS_PORTS", "8001,8002,8003,8004,8005").split(",") if port.strip().isdigit()]
    if not OXYLABS_PORTS:  # Fallback if no valid ports
        OXYLABS_PORTS = [8001, 8002, 8003, 8004, 8005]
except Exception as e:
    print(f"Warning: Error parsing OXYLABS_PORTS: {e}. Using default ports.")
    OXYLABS_PORTS = [8001, 8002, 8003, 8004, 8005]

class ProxyManager:
    """
    Manages a pool of proxies for rotation during requests.
    Tracks proxy success/failure and prioritizes working proxies.
    """
    def __init__(self, proxies_file: str = PROXIES_FILE, use_proxies: bool = False):
        self.proxies = []
        self.working_proxies = set()
        self.failed_proxies = {}
        self.use_proxies = use_proxies
        self.current_index = 0
        
        if use_proxies:
            self.load_proxies(proxies_file)
            self.add_oxylabs_proxies()
            print(f"Loaded {len(self.proxies)} proxies")
    
    def add_oxylabs_proxies(self):
        """Add Oxylabs proxies to the proxy pool if credentials are available"""
        if not OXYLABS_USERNAME or not OXYLABS_PASSWORD:
            return
        
        for port in OXYLABS_PORTS:
            proxy_url = f"http://user-{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}:{port}"
            if proxy_url not in self.proxies:
                self.proxies.append(proxy_url)
                print(f"Added Oxylabs proxy on port {port}")
    
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
                return {}  # No suitable proxy found
        
        # Parse the proxy URL to get the scheme and actual proxy address
        try:
            if proxy_url.startswith(('http://', 'https://')):
                scheme = proxy_url.split('://')[0]
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
                    for scheme, proxy in current_proxy.items():
                        current_proxy_url = proxy
                        break
                    print(f"Using proxy: {current_proxy_url} for image: {url}")
                else:
                    print(f"No proxy available, using direct connection for image: {url}")
            
            response = requests.get(url, headers=headers, proxies=current_proxy, timeout=timeout)
            response.raise_for_status()
            
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
                
            return True
            
        except requests.exceptions.ProxyError as e:
            print(f"Proxy error for image {url}: {e}")
            
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
        if 'boto3' not in globals():
            print("boto3 is not installed. Skipping upload to Cloudflare R2.")
            return None
        
        # Check if Cloudflare credentials are available
        if not CLOUDFLARE_ACCESS_KEY_ID or not CLOUDFLARE_SECRET_ACCESS_KEY or not CLOUDFLARE_ENDPOINT:
            print("Cloudflare R2 credentials not set. Skipping upload.")
            return None
        
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
            CLOUDFLARE_BUCKET_NAME, 
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

def process_image_urls(limit=None, minifigs_only=False, start_index=0, batch_size=0):
    """Process image URLs in the catalog data.
    
    Args:
        limit (int, optional): Limit the number of images to process. Defaults to None (process all).
        minifigs_only (bool, optional): Process only minifigure images. Defaults to False.
        start_index (int, optional): Start index for batch processing. Defaults to 0.
        batch_size (int, optional): Batch size for processing. Defaults to 0 (process all).
    """
    print("Processing image URLs in catalog data...")
    
    # Load existing image mapping if it exists
    image_mapping = {}
    if os.path.exists(IMAGE_MAPPING_FILE):
        with open(IMAGE_MAPPING_FILE, 'r') as f:
            image_mapping = json.load(f)
    
    # Create a set of already processed URLs (both original and processed)
    processed_urls = set(image_mapping.keys()).union(set(image_mapping.values()))
    
    # Track processed item IDs to handle multiple images for the same item
    processed_item_ids = {}
    for url, mapped_url in image_mapping.items():
        # Extract item ID from the mapped URL
        if '/set/' in mapped_url:
            # Extract set number from the end of the URL
            match = re.search(r'-([^-]+)\.jpg$', mapped_url)
            if match:
                item_id = match.group(1)
                processed_item_ids[item_id] = processed_item_ids.get(item_id, 0) + 1
        elif '/minifig/' in mapped_url:
            # Extract fig number from the end of the URL
            match = re.search(r'-(fig-\d+)\.jpg$', mapped_url)
            if match:
                item_id = match.group(1)
                processed_item_ids[item_id] = processed_item_ids.get(item_id, 0) + 1
    
    # Initialize items list
    items_with_images = []
    
    # Process sets.csv for img_url if not minifigs_only
    if not minifigs_only:
        sets_csv = os.path.join(EXTRACTED_DIR, "sets.csv")
        if not os.path.exists(sets_csv):
            print(f"Sets CSV file not found: {sets_csv}")
            if minifigs_only:
                return
        else:
            # Read the sets CSV file
            with open(sets_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    img_url = row.get('img_url', '')
                    if is_valid_image_url(img_url) and img_url not in processed_urls:
                        # Get theme name if available
                        theme_id = row.get('theme_id', '')
                        theme_name = get_theme_name(theme_id) if theme_id else ''
                        
                        items_with_images.append({
                            'set_num': row.get('set_num', ''),
                            'name': row.get('name', ''),
                            'theme_name': theme_name,
                            'img_url': img_url,
                            'type': 'set'
                        })
    
    # Process minifigs.csv for img_url if limit allows or if minifigs_only
    minifigs_csv = os.path.join(EXTRACTED_DIR, "minifigs.csv")
    if os.path.exists(minifigs_csv) and (minifigs_only or not limit or len(items_with_images) < limit):
        with open(minifigs_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Skip rows before start_index
            for _ in range(start_index):
                try:
                    next(reader)
                except StopIteration:
                    break
            
            # Read rows up to batch_size if specified
            row_count = 0
            for row in reader:
                if batch_size > 0 and row_count >= batch_size:
                    break
                
                img_url = row.get('img_url', '')
                if is_valid_image_url(img_url) and img_url not in processed_urls:
                    items_with_images.append({
                        'set_num': row.get('fig_num', ''),
                        'name': row.get('name', ''),
                        'theme_name': '',  # Minifigs don't have themes in the CSV
                        'img_url': img_url,
                        'type': 'minifig'
                    })
                    
                    # Apply limit if specified
                    if limit and len(items_with_images) >= limit:
                        break
                
                row_count += 1
    
    print(f"Found {len(items_with_images)} items with images to process")
    
    # Track failed downloads
    failed_downloads = []
    
    # Process images in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        
        for item_data in items_with_images:
            img_url = item_data['img_url']
            item_id = item_data['set_num']
            item_type = item_data['type']
            item_name = item_data['name']
            theme_name = item_data['theme_name']
            
            # Skip if already processed
            if img_url in processed_urls:
                continue
            
            # Check if we already have images for this item
            image_count = processed_item_ids.get(item_id, 0)
            # Increment the count for this item
            processed_item_ids[item_id] = image_count + 1
            
            # Create SEO-friendly filename
            if item_type == 'set':
                # Format: lego-[theme]-[set-name]-[set-number]-[view].jpg
                theme_part = f"{theme_name.lower()}-" if theme_name else ""
                
                # Add view suffix if this is not the first image
                view_suffix = ""
                if image_count > 0:
                    # Use descriptive suffixes for the first few images
                    if image_count == 1:
                        view_suffix = "-alt"
                    elif image_count == 2:
                        view_suffix = "-back"
                    elif image_count == 3:
                        view_suffix = "-side"
                    else:
                        # For more images, use a numeric suffix
                        view_suffix = f"-view{image_count}"
                
                filename = f"lego-{theme_part}{item_name.lower()}-{item_id}{view_suffix}"
                
                # Clean up the filename
                filename = re.sub(r'[^a-zA-Z0-9-]', '-', filename)
                filename = re.sub(r'-+', '-', filename)
                filename = filename.strip('-')
                
                # Ensure the filename is not too long
                if len(filename) > 70:  # Increased length to accommodate view suffix
                    # Try to preserve the set number and view suffix at the end
                    suffix_len = len(f"-{item_id}{view_suffix}")
                    base = filename[:70-suffix_len]
                    last_dash = base.rfind('-')
                    if last_dash > 40:  # Only truncate at dash if we're not losing too much
                        base = base[:last_dash]
                    filename = f"{base}-{item_id}{view_suffix}"
                
                # Add extension
                filename = f"{filename}.jpg"
            else:  # minifig
                # Format: lego-minifig-[name]-[fig-number]-[view].jpg
                clean_name = re.sub(r'[^a-zA-Z0-9]', '-', item_name)
                clean_name = re.sub(r'-+', '-', clean_name)
                clean_name = clean_name.strip('-').lower()
                
                # Add view suffix if this is not the first image
                view_suffix = ""
                if image_count > 0:
                    # Use descriptive suffixes for the first few images
                    if image_count == 1:
                        view_suffix = "-alt"
                    elif image_count == 2:
                        view_suffix = "-back"
                    elif image_count == 3:
                        view_suffix = "-side"
                    else:
                        # For more images, use a numeric suffix
                        view_suffix = f"-view{image_count}"
                
                # Limit name length
                if len(clean_name) > 40:
                    clean_name = clean_name[:40]
                    last_dash = clean_name.rfind('-')
                    if last_dash > 30:  # Only truncate at dash if we're not losing too much
                        clean_name = clean_name[:last_dash]
                
                filename = f"lego-minifig-{clean_name}-{item_id}{view_suffix}.jpg"
            
            local_path = os.path.join(IMAGES_DIR, filename)
            r2_object_key = f"catalog/{item_type}/{filename}"
            
            # Submit download and optimization task
            future = executor.submit(
                download_and_optimize_image,
                img_url,
                local_path
            )
            futures.append((future, img_url, local_path, r2_object_key, item_data))
        
        # Process results
        for future, img_url, local_path, r2_object_key, item_data in futures:
            try:
                if future.result():
                    # Upload to Cloudflare R2
                    cloudflare_url = upload_to_cloudflare_r2(local_path, r2_object_key)
                    
                    # Update image mapping
                    if cloudflare_url:
                        image_mapping[img_url] = cloudflare_url
                        print(f"Processed image: {img_url} -> {cloudflare_url}")
                    else:
                        print(f"Failed to upload image to Cloudflare R2: {img_url}")
                        failed_downloads.append({
                            'url': img_url,
                            'item_id': item_data['set_num'],
                            'name': item_data['name'],
                            'type': item_data['type'],
                            'error': 'Failed to upload to Cloudflare R2'
                        })
                else:
                    print(f"Failed to download/process image: {img_url}")
                    failed_downloads.append({
                        'url': img_url,
                        'item_id': item_data['set_num'],
                        'name': item_data['name'],
                        'type': item_data['type'],
                        'error': 'Failed to download or process image after 3 retries'
                    })
            except Exception as e:
                print(f"Error processing image {img_url}: {str(e)}")
                failed_downloads.append({
                    'url': img_url,
                    'item_id': item_data['set_num'],
                    'name': item_data['name'],
                    'type': item_data['type'],
                    'error': str(e)
                })
    
    # Save updated image mapping
    with open(IMAGE_MAPPING_FILE, 'w') as f:
        json.dump(image_mapping, f, indent=2)
    
    # Save failed downloads to a log file
    if failed_downloads:
        failed_log_file = os.path.join(IMAGES_DIR, "failed_downloads.json")
        with open(failed_log_file, 'w') as f:
            json.dump(failed_downloads, f, indent=2)
        print(f"Saved {len(failed_downloads)} failed downloads to {failed_log_file}")
    
    print(f"Processed {len(image_mapping)} images. Mapping saved to {IMAGE_MAPPING_FILE}")
    
    return len(image_mapping), len(failed_downloads)

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

def main():
    parser = argparse.ArgumentParser(description="Extract LEGO catalog data and process images")
    parser.add_argument("--extract-only", action="store_true", help="Only extract .gz files without processing images")
    parser.add_argument("--process-images", action="store_true", help="Process images without extracting .gz files")
    parser.add_argument("--update-csv", action="store_true", help="Update CSV files with new image URLs")
    parser.add_argument("--limit", type=int, help="Limit the number of images to process")
    parser.add_argument("--minifigs-only", action="store_true", help="Process only minifigure images")
    parser.add_argument("--test", action="store_true", help="Run test function for multiple images")
    parser.add_argument("--use-proxies", action="store_true", help="Use proxy rotation for image downloads")
    parser.add_argument("--proxies-file", default=PROXIES_FILE, help="File containing proxy URLs")
    parser.add_argument("--start-index", type=int, default=0, help="Start index for batch processing")
    parser.add_argument("--batch-size", type=int, default=0, help="Batch size for processing (0 means process all)")
    
    args = parser.parse_args()
    
    # Initialize the global proxy manager if proxy usage is requested
    global proxy_manager
    proxy_manager = ProxyManager(proxies_file=args.proxies_file, use_proxies=args.use_proxies)
    
    # Run test function if requested
    if args.test:
        test_multiple_images()
        return
    
    # Ensure directories exist
    ensure_directories()
    
    # Extract .gz files if requested or if no specific action is requested
    if args.extract_only or (not args.process_images and not args.update_csv and not args.test):
        extract_gz_files()
    
    # Process images if requested or if no specific action is requested
    if args.process_images or (not args.extract_only and not args.update_csv and not args.test):
        successful, failed = process_image_urls(
            limit=args.limit, 
            minifigs_only=args.minifigs_only,
            start_index=args.start_index,
            batch_size=args.batch_size
        )
        print(f"Summary: {successful} images processed successfully, {failed} images failed")
    
    # Update CSV files if requested or if no specific action is requested
    if args.update_csv or (not args.extract_only and not args.process_images and not args.test):
        update_csv_with_new_urls()
    
    print("Done!")

if __name__ == "__main__":
    main() 