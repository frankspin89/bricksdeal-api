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
    
    # Add prefix if provided and not already in the base_name
    if prefix and prefix not in base_name:
        components.append(prefix)
    
    # Add name if provided
    if name:
        # Clean up the name for URL use
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', name)
        clean_name = re.sub(r'-+', '-', clean_name)
        clean_name = clean_name.strip('-').lower()
        
        # Limit name length
        if len(clean_name) > 30:
            # Try to keep whole words by finding the last space before the limit
            clean_name = clean_name[:30]
            last_dash = clean_name.rfind('-')
            if last_dash > 20:  # Only truncate at dash if we're not losing too much
                clean_name = clean_name[:last_dash]
        
        components.append(clean_name)
    
    # Add a cleaned version of the original filename if needed
    if not components:
        clean_base = re.sub(r'[^a-zA-Z0-9]', '-', base_name)
        clean_base = re.sub(r'-+', '-', clean_base)
        clean_base = clean_base.strip('-')
        components.append(clean_base)
    
    # Join components and ensure total length is reasonable
    result = "-".join(components)
    if len(result) > 60:
        result = result[:60]
        # Try to end at a dash to avoid cutting words
        last_dash = result.rfind('-')
        if last_dash > 50:  # Only truncate at dash if we're not losing too much
            result = result[:last_dash]
    
    return f"{result}{ext}"

def download_and_optimize_image(url, output_path):
    """Download and optimize an image."""
    try:
        response = requests.get(url, timeout=30)
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
        
        return True
    except Exception as e:
        print(f"Error downloading/optimizing image {url}: {str(e)}")
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

def process_image_urls(limit=None, minifigs_only=False):
    """Process image URLs in the catalog data.
    
    Args:
        limit (int, optional): Limit the number of images to process. Defaults to None (process all).
        minifigs_only (bool, optional): Process only minifigure images. Defaults to False.
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
                        # Apply limit if specified
                        if limit and len(items_with_images) >= limit:
                            break
    
    # Process minifigs.csv for img_url if limit allows or if minifigs_only
    minifigs_csv = os.path.join(EXTRACTED_DIR, "minifigs.csv")
    if os.path.exists(minifigs_csv) and (minifigs_only or not limit or len(items_with_images) < limit):
        with open(minifigs_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
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
    
    print(f"Found {len(items_with_images)} items with images to process")
    
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
            futures.append((future, img_url, local_path, r2_object_key))
        
        # Process results
        for future, img_url, local_path, r2_object_key in futures:
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
            except Exception as e:
                print(f"Error processing image {img_url}: {str(e)}")
    
    # Save updated image mapping
    with open(IMAGE_MAPPING_FILE, 'w') as f:
        json.dump(image_mapping, f, indent=2)
    
    print(f"Processed {len(image_mapping)} images. Mapping saved to {IMAGE_MAPPING_FILE}")

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
    
    args = parser.parse_args()
    
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
        process_image_urls(limit=args.limit, minifigs_only=args.minifigs_only)
    
    # Update CSV files if requested or if no specific action is requested
    if args.update_csv or (not args.extract_only and not args.process_images and not args.test):
        update_csv_with_new_urls()
    
    print("Done!")

if __name__ == "__main__":
    main() 