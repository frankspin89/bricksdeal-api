#!/usr/bin/env python3
import os
import json
import argparse
import subprocess
import time
import datetime
from typing import Dict, List, Any, Optional
import re
import html
import requests
from dotenv import load_dotenv
import shutil
from urllib.parse import urlparse, unquote
import mimetypes

# Try to import boto3, but make it optional
try:
    import boto3
    from botocore.client import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("Warning: boto3 is not installed. Cloudflare R2 upload functionality will be disabled.")
    print("To enable Cloudflare R2 upload, install boto3: pip install boto3")

# Load environment variables from .env file
load_dotenv()

# Constants
INPUT_DIR = "input"
OUTPUT_DIR = "output"
PRODUCTS_DIR = os.path.join(OUTPUT_DIR, "products")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
PRICE_HISTORY_DIR = os.path.join(OUTPUT_DIR, "price_history")
SUMMARIES_DIR = os.path.join(OUTPUT_DIR, "summaries")
URLS_FILE = os.path.join(INPUT_DIR, "lego_urls.json")
PROCESSED_URLS_FILE = os.path.join(SUMMARIES_DIR, "processed_urls.json")
ANALYSIS_DIR = os.path.join(OUTPUT_DIR, "analysis")
ARTICLES_DIR = os.path.join(OUTPUT_DIR, "articles")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

# Cloudflare configuration
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID", "")
CLOUDFLARE_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY", "")
CLOUDFLARE_R2_BUCKET = os.environ.get("CLOUDFLARE_R2_BUCKET", "lego-images")
CLOUDFLARE_DOMAIN = os.environ.get("CLOUDFLARE_DOMAIN", "images.example.com")
CLOUDFLARE_R2_ENDPOINT = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"

def setup_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PRICE_HISTORY_DIR, exist_ok=True)
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    print(f"Ensured all directories exist")

def run_command(command: List[str]) -> bool:
    """Run a command and return whether it was successful."""
    print(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings/Errors: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def scrape_new_products(max_pages: Optional[int] = None) -> bool:
    """Scrape new LEGO products and save URLs to JSON."""
    command = ["python3", "scrape_new_products.py"]
    if max_pages:
        command.extend(["--max-pages", str(max_pages)])
    return run_command(command)

def process_urls(max_workers: int = 3, use_proxies: bool = False, timeout: int = 30) -> bool:
    """Process URLs from the JSON file."""
    command = [
        "python3", 
        "scrape_lego_direct.py", 
        "--file", URLS_FILE, 
        "--max-workers", str(max_workers),
        "--skip-processed"
    ]
    if use_proxies:
        command.append("--use-proxies")
        command.extend(["--timeout", str(timeout)])
    return run_command(command)

def list_processed_urls() -> List[str]:
    """List processed URLs and return them."""
    command = ["python3", "scrape_lego_direct.py", "--list-processed"]
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
        
        # Extract URLs from the output
        urls = []
        for line in result.stdout.splitlines():
            if line.startswith("[SUCCESS]"):
                url = line.split("[SUCCESS]")[1].split("(Product ID:")[0].strip()
                urls.append(url)
        return urls
    except subprocess.CalledProcessError as e:
        print(f"Error listing processed URLs: {e}")
        return []

def analyze_raw_data():
    """Analyze raw data files to extract additional insights."""
    print("\n=== Analyzing Raw Data ===")
    
    # Get all raw data files
    raw_files = [f for f in os.listdir(RAW_DIR) if f.startswith("raw_lego_product_") and f.endswith(".json")]
    print(f"Found {len(raw_files)} raw data files to analyze")
    
    # Initialize counters and data structures
    total_products = 0
    available_products = 0
    out_of_stock_products = 0
    price_ranges = {"0-25": 0, "25-50": 0, "50-100": 0, "100-200": 0, "200+": 0}
    themes = {}
    age_ranges = {}
    piece_counts = {}
    
    # Process each raw file
    for raw_file in raw_files:
        file_path = os.path.join(RAW_DIR, raw_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            total_products += 1
            
            # Extract availability
            availability = None
            if "meta_tags" in data and "product:availability" in data["meta_tags"]:
                availability = data["meta_tags"]["product:availability"]
            elif "structured_data" in data and isinstance(data["structured_data"], list):
                for item in data["structured_data"]:
                    if isinstance(item, dict) and "offers" in item:
                        if isinstance(item["offers"], dict) and "availability" in item["offers"]:
                            availability = item["offers"]["availability"]
                            if "http" in availability:
                                availability = availability.split("/")[-1]
                        elif isinstance(item["offers"], list):
                            for offer in item["offers"]:
                                if isinstance(offer, dict) and "availability" in offer:
                                    availability = offer["availability"]
                                    if "http" in availability:
                                        availability = availability.split("/")[-1]
            
            if availability:
                if "instock" in availability.lower() or "in_stock" in availability.lower():
                    available_products += 1
                elif "outofstock" in availability.lower() or "out_of_stock" in availability.lower():
                    out_of_stock_products += 1
            
            # Extract price
            price = None
            if "meta_tags" in data and "product:price:amount" in data["meta_tags"]:
                try:
                    price = float(data["meta_tags"]["product:price:amount"])
                except (ValueError, TypeError):
                    pass
            elif "structured_data" in data and isinstance(data["structured_data"], list):
                for item in data["structured_data"]:
                    if isinstance(item, dict) and "offers" in item:
                        if isinstance(item["offers"], dict) and "price" in item["offers"]:
                            try:
                                price = float(item["offers"]["price"])
                            except (ValueError, TypeError):
                                pass
                        elif isinstance(item["offers"], list):
                            for offer in item["offers"]:
                                if isinstance(offer, dict) and "price" in offer:
                                    try:
                                        price = float(offer["price"])
                                    except (ValueError, TypeError):
                                        pass
            
            if price:
                if price < 25:
                    price_ranges["0-25"] += 1
                elif price < 50:
                    price_ranges["25-50"] += 1
                elif price < 100:
                    price_ranges["50-100"] += 1
                elif price < 200:
                    price_ranges["100-200"] += 1
                else:
                    price_ranges["200+"] += 1
            
            # Extract theme
            theme = None
            if "structured_data" in data and isinstance(data["structured_data"], list):
                for item in data["structured_data"]:
                    if isinstance(item, dict) and "brand" in item:
                        if isinstance(item["brand"], dict) and "name" in item["brand"]:
                            theme = item["brand"]["name"]
                    if isinstance(item, dict) and "category" in item:
                        theme = item["category"]
            
            if theme:
                themes[theme] = themes.get(theme, 0) + 1
            
            # Extract age range
            age_range = None
            if "structured_data" in data and isinstance(data["structured_data"], list):
                for item in data["structured_data"]:
                    if isinstance(item, dict) and "audience" in item:
                        if isinstance(item["audience"], dict) and "suggestedMinAge" in item["audience"]:
                            try:
                                min_age = int(item["audience"]["suggestedMinAge"])
                                age_range = f"{min_age}+"
                            except (ValueError, TypeError):
                                pass
            
            if age_range:
                age_ranges[age_range] = age_ranges.get(age_range, 0) + 1
            
            # Extract piece count
            piece_count = None
            if "structured_data" in data and isinstance(data["structured_data"], list):
                for item in data["structured_data"]:
                    if isinstance(item, dict) and "additionalProperty" in item:
                        if isinstance(item["additionalProperty"], list):
                            for prop in item["additionalProperty"]:
                                if isinstance(prop, dict) and prop.get("name") == "piece count":
                                    try:
                                        piece_count = int(prop["value"])
                                    except (ValueError, TypeError):
                                        pass
            
            if piece_count:
                if piece_count < 100:
                    piece_counts["<100"] = piece_counts.get("<100", 0) + 1
                elif piece_count < 500:
                    piece_counts["100-499"] = piece_counts.get("100-499", 0) + 1
                elif piece_count < 1000:
                    piece_counts["500-999"] = piece_counts.get("500-999", 0) + 1
                else:
                    piece_counts["1000+"] = piece_counts.get("1000+", 0) + 1
            
        except Exception as e:
            print(f"Error processing {raw_file}: {e}")
    
    # Prepare analysis results
    analysis = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_products": total_products,
        "availability": {
            "available": available_products,
            "out_of_stock": out_of_stock_products,
            "unknown": total_products - available_products - out_of_stock_products
        },
        "price_ranges": price_ranges,
        "themes": themes,
        "age_ranges": age_ranges,
        "piece_counts": piece_counts
    }
    
    # Save analysis results
    analysis_file = os.path.join(ANALYSIS_DIR, f"lego_analysis_{datetime.datetime.now().strftime('%Y-%m-%d')}.json")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    # Also save as latest analysis
    latest_analysis_file = os.path.join(ANALYSIS_DIR, "latest_analysis.json")
    with open(latest_analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"Analysis complete. Results saved to {analysis_file}")
    
    # Print summary
    print("\n=== Analysis Summary ===")
    print(f"Total products analyzed: {total_products}")
    print(f"Available products: {available_products} ({available_products/total_products*100:.1f}%)")
    print(f"Out of stock products: {out_of_stock_products} ({out_of_stock_products/total_products*100:.1f}%)")
    
    print("\nPrice Ranges:")
    for price_range, count in price_ranges.items():
        if count > 0:
            print(f"  {price_range} EUR: {count} products ({count/total_products*100:.1f}%)")
    
    print("\nTop Themes:")
    sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
    for theme, count in sorted_themes[:5]:
        print(f"  {theme}: {count} products ({count/total_products*100:.1f}%)")
    
    print("\nAge Ranges:")
    for age_range, count in sorted(age_ranges.items()):
        print(f"  {age_range}: {count} products ({count/total_products*100:.1f}%)")
    
    print("\nPiece Counts:")
    for piece_range, count in sorted(piece_counts.items()):
        if count > 0:
            print(f"  {piece_range} pieces: {count} products ({count/total_products*100:.1f}%)")
    
    return analysis

def extract_additional_data():
    """Extract additional data from raw files and enhance product files."""
    print("\n=== Extracting Additional Data ===")
    
    # Get all raw data files
    raw_files = [f for f in os.listdir(RAW_DIR) if f.startswith("raw_lego_product_") and f.endswith(".json")]
    print(f"Found {len(raw_files)} raw data files to process")
    
    for raw_file in raw_files:
        try:
            file_product_id = raw_file.replace("raw_lego_product_", "").replace(".json", "")
            raw_path = os.path.join(RAW_DIR, raw_file)
            product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{file_product_id}.json")
            
            # Skip if product file doesn't exist
            if not os.path.exists(product_path):
                print(f"Skipping {raw_file} - no corresponding product file found")
                continue
            
            # Load raw data
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Load product data
            with open(product_path, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            
            # Extract the correct product ID (set number)
            correct_product_id = None
            
            # Try to get product ID from meta tags
            if "meta_tags" in raw_data and "product:retailer_item_id" in raw_data["meta_tags"]:
                correct_product_id = raw_data["meta_tags"]["product:retailer_item_id"]
            
            # If not found, try to extract from title or URL
            if not correct_product_id:
                # Try to extract from title
                if "html_title" in raw_data:
                    title = raw_data["html_title"]
                    id_match = re.search(r'(\d{5,})', title)
                    if id_match:
                        correct_product_id = id_match.group(1)
                
                # Try to extract from URL
                if not correct_product_id and "url" in raw_data:
                    url = raw_data["url"]
                    id_match = re.search(r'product/[^/]*?-(\d{5,})', url)
                    if id_match:
                        correct_product_id = id_match.group(1)
            
            # Check if we need to rename files due to a different product ID
            if correct_product_id and correct_product_id != file_product_id:
                print(f"Found more accurate product ID: {file_product_id} -> {correct_product_id}")
                
                # Define new file paths
                new_raw_path = os.path.join(RAW_DIR, f"raw_lego_product_{correct_product_id}.json")
                new_product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{correct_product_id}.json")
                
                # Check if the new files already exist
                if os.path.exists(new_raw_path) or os.path.exists(new_product_path):
                    print(f"Cannot rename files - target files already exist for product ID {correct_product_id}")
                else:
                    # Rename the files
                    os.rename(raw_path, new_raw_path)
                    os.rename(product_path, new_product_path)
                    print(f"Renamed files to use correct product ID: {correct_product_id}")
                    
                    # Update paths for further processing
                    raw_path = new_raw_path
                    product_path = new_product_path
                    
                    # Update processed URLs tracking
                    try:
                        processed_urls_path = os.path.join(os.path.dirname(RAW_DIR), "summaries", "processed_urls.json")
                        if os.path.exists(processed_urls_path):
                            with open(processed_urls_path, 'r', encoding='utf-8') as f:
                                processed_urls = json.load(f)
                            
                            # Find and update entries with the old product ID
                            updated = False
                            for url, data in processed_urls.items():
                                if data.get("product_id") == file_product_id:
                                    processed_urls[url]["product_id"] = correct_product_id
                                    updated = True
                                    print(f"Updated processed URL entry: {url} with product ID {file_product_id} -> {correct_product_id}")
                            
                            if updated:
                                with open(processed_urls_path, 'w', encoding='utf-8') as f:
                                    json.dump(processed_urls, f, indent=2, ensure_ascii=False)
                                print(f"Updated processed URLs tracking with correct product ID: {correct_product_id}")
                    except Exception as e:
                        print(f"Error updating processed URLs: {str(e)}")
                        # Continue processing even if updating processed URLs fails
                    
                    # Update price history files
                    try:
                        price_history_dir = os.path.join(os.path.dirname(RAW_DIR), "price_history")
                        old_price_history_path = os.path.join(price_history_dir, f"price_history_{file_product_id}.json")
                        new_price_history_path = os.path.join(price_history_dir, f"price_history_{correct_product_id}.json")
                        
                        if os.path.exists(old_price_history_path):
                            if os.path.exists(new_price_history_path):
                                # If both files exist, merge them
                                with open(old_price_history_path, 'r', encoding='utf-8') as f:
                                    old_history = json.load(f)
                                with open(new_price_history_path, 'r', encoding='utf-8') as f:
                                    new_history = json.load(f)
                                
                                # Combine histories and remove duplicates
                                combined_history = old_history + new_history
                                # Sort by date and remove duplicates (keeping the latest entry for each date)
                                date_price_map = {}
                                for entry in combined_history:
                                    date = entry.get("date", "")
                                    if date:
                                        date_price_map[date] = entry
                                
                                merged_history = list(date_price_map.values())
                                merged_history.sort(key=lambda x: x.get("date", ""))
                                
                                # Save merged history
                                with open(new_price_history_path, 'w', encoding='utf-8') as f:
                                    json.dump(merged_history, f, indent=2, ensure_ascii=False)
                                
                                # Remove old file
                                os.remove(old_price_history_path)
                                print(f"Merged price history files for product ID: {correct_product_id}")
                            else:
                                # Simply rename the file
                                os.rename(old_price_history_path, new_price_history_path)
                                print(f"Renamed price history file to use correct product ID: {correct_product_id}")
                    except Exception as e:
                        print(f"Error updating price history files: {str(e)}")
                        # Continue processing even if updating price history fails
            
            # Create a clean, structured product data object
            product_info = {
                "id": correct_product_id or file_product_id,  # Use correct ID if found, otherwise use file ID
                "title": raw_data.get("html_title", ""),
                "url": raw_data.get("url", ""),
                "status": "unknown"
            }
            
            # Extract availability information
            if "meta_tags" in raw_data and "product:availability" in raw_data["meta_tags"]:
                availability = raw_data["meta_tags"]["product:availability"]
                product_info["status"] = availability
            
            # Extract price information
            price_info = {}
            current_price = None
            
            # Try to get price from meta tags
            if "meta_tags" in raw_data:
                meta_tags = raw_data["meta_tags"]
                if "product:price:amount" in meta_tags and meta_tags["product:price:amount"]:
                    try:
                        price = float(meta_tags["product:price:amount"])
                        if price > 0:  # Only add if price is valid
                            current_price = price
                            price_info["currency"] = meta_tags.get("product:price:currency", "EUR")
                    except (ValueError, TypeError):
                        pass
            
            # Clean up price history by removing invalid entries (price = 0)
            valid_price_history = []
            if "metadata" in product_data and "price_history" in product_data["metadata"]:
                price_history = product_data["metadata"]["price_history"]
                valid_price_history = [entry for entry in price_history if entry.get("price", 0) > 0]
                
                # If we don't have a current price but have valid price history
                if not current_price and valid_price_history:
                    latest_valid = max(valid_price_history, key=lambda x: x.get("date", ""))
                    current_price = latest_valid.get("price")
                    price_info["currency"] = latest_valid.get("currency", "EUR")
                    price_info["note"] = "Price from history (product may be retired/unavailable)"
            
            # Add price information to product_info
            if current_price:
                price_info["amount"] = current_price
                product_info["price"] = price_info
                
                # Add current price to price history if it's not already there
                current_time = datetime.datetime.now().isoformat()
                new_price_entry = {
                    "date": current_time,
                    "price": current_price,
                    "currency": price_info.get("currency", "EUR")
                }
                
                # Check if this exact price is already in the history
                price_already_recorded = False
                for entry in valid_price_history:
                    if entry.get("price") == current_price and entry.get("currency") == new_price_entry["currency"]:
                        price_already_recorded = True
                        break
                
                # Add to history if not already there
                if not price_already_recorded:
                    valid_price_history.append(new_price_entry)
            
            # Update price history in metadata
            if "metadata" not in product_data:
                product_data["metadata"] = {}
            product_data["metadata"]["price_history"] = valid_price_history
            
            # Extract main product image
            if "meta_tags" in raw_data and "og:image" in raw_data["meta_tags"]:
                product_info["image"] = raw_data["meta_tags"]["og:image"]
                
                # Create high-res version with 2x DPI
                main_image = product_info["image"]
                high_res_main_image = main_image
                if "?" in high_res_main_image:
                    # Replace or add DPI parameter
                    if "dpr=" in high_res_main_image:
                        high_res_main_image = re.sub(r'dpr=\d+', 'dpr=2', high_res_main_image)
                    else:
                        high_res_main_image += "&dpr=2"
                else:
                    high_res_main_image += "?dpr=2"
                product_info["high_res_image"] = high_res_main_image
            
            # Extract all images
            images = []
            high_res_images = []
            
            # Extract from structured data
            if "structured_data" in raw_data and isinstance(raw_data["structured_data"], list):
                for item in raw_data["structured_data"]:
                    if isinstance(item, dict) and "image" in item:
                        if isinstance(item["image"], list):
                            for img in item["image"]:
                                if img not in images:
                                    images.append(img)
                                    # Create high-res version with 2x DPI
                                    high_res_img = img
                                    if "?" in high_res_img:
                                        # Replace or add DPI parameter
                                        if "dpr=" in high_res_img:
                                            high_res_img = re.sub(r'dpr=\d+', 'dpr=2', high_res_img)
                                        else:
                                            high_res_img += "&dpr=2"
                                    else:
                                        high_res_img += "?dpr=2"
                                    high_res_images.append(high_res_img)
                        elif isinstance(item["image"], str) and item["image"] not in images:
                            images.append(item["image"])
                            # Create high-res version with 2x DPI
                            high_res_img = item["image"]
                            if "?" in high_res_img:
                                # Replace or add DPI parameter
                                if "dpr=" in high_res_img:
                                    high_res_img = re.sub(r'dpr=\d+', 'dpr=2', high_res_img)
                                else:
                                    high_res_img += "&dpr=2"
                            else:
                                high_res_img += "?dpr=2"
                            high_res_images.append(high_res_img)
            
            # Extract from meta tags
            if "meta_tags" in raw_data and "og:image" in raw_data["meta_tags"]:
                og_image = raw_data["meta_tags"]["og:image"]
                if og_image not in images:
                    images.append(og_image)
                    # Create high-res version with 2x DPI
                    high_res_img = og_image
                    if "?" in high_res_img:
                        # Replace or add DPI parameter
                        if "dpr=" in high_res_img:
                            high_res_img = re.sub(r'dpr=\d+', 'dpr=2', high_res_img)
                        else:
                            high_res_img += "&dpr=2"
                    else:
                        high_res_img += "?dpr=2"
                    high_res_images.append(high_res_img)
            
            # Extract from raw data images
            if "images" in raw_data and isinstance(raw_data["images"], list):
                for img in raw_data["images"]:
                    if img not in images:
                        images.append(img)
                        # Create high-res version with 2x DPI
                        high_res_img = img
                        if "?" in high_res_img:
                            # Replace or add DPI parameter
                            if "dpr=" in high_res_img:
                                high_res_img = re.sub(r'dpr=\d+', 'dpr=2', high_res_img)
                            else:
                                high_res_img += "&dpr=2"
                        else:
                            high_res_img += "?dpr=2"
                        high_res_images.append(high_res_img)
            
            # NEW: Extract all unique image URLs from the raw data
            unique_base_urls = set()
            if isinstance(raw_data, dict):
                raw_data_str = json.dumps(raw_data)
                # Find all image URLs for this product
                image_urls = re.findall(r'https://www\.lego\.com/cdn/cs/set/assets/[^"\']*?(?:71837|' + re.escape(product_info["id"]) + r')[^"\']*?\.(?:jpg|png)', raw_data_str)
                
                # Process each URL to get the base URL without size parameters
                for url in image_urls:
                    # Extract the base URL without parameters
                    base_url = url.split('?')[0]
                    if base_url not in unique_base_urls and not base_url.endswith('.mp4'):
                        unique_base_urls.add(base_url)
                        
                        # Create a high-quality version with optimal parameters
                        high_quality_url = f"{base_url}?fit=bounds&format=jpg&quality=80&width=1500&height=1500&dpr=1"
                        high_res_url = f"{base_url}?fit=bounds&format=jpg&quality=80&width=1500&height=1500&dpr=2"
                        
                        if high_quality_url not in images:
                            images.append(high_quality_url)
                        if high_res_url not in high_res_images:
                            high_res_images.append(high_res_url)
            
            if images:
                product_info["images"] = images
            
            if high_res_images:
                product_info["high_res_images"] = high_res_images
            
            # Extract product specifications
            specs = {}
            
            # Try to extract piece count and age range from markdown content
            if "content" in product_data and "markdown" in product_data["content"]:
                markdown_content = product_data["content"]["markdown"]
                
                # Try to extract from English specifications
                if "en" in markdown_content and "specifications" in markdown_content["en"]:
                    spec_text = markdown_content["en"]["specifications"]
                    
                    # Extract piece count - try different patterns
                    piece_count_match = re.search(r"Piece Count:?\s*(\d+,?\d*)", spec_text, re.IGNORECASE) or \
                                       re.search(r"\*\*Piece Count:?\*\*\s*(\d+,?\d*)", spec_text, re.IGNORECASE) or \
                                       re.search(r"\*\*Aantal onderdelen:?\*\*\s*(\d+\.?\d*)", spec_text, re.IGNORECASE)
                    if piece_count_match:
                        try:
                            # Remove commas and convert to integer
                            piece_count_str = piece_count_match.group(1).replace(',', '').replace('.', '')
                            specs["piece_count"] = int(piece_count_str)
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract age range - try different patterns
                    age_range_match = re.search(r"Age Range:?\s*(\d+)\+", spec_text, re.IGNORECASE) or \
                                     re.search(r"\*\*Age Range:?\*\*\s*(\d+)\+", spec_text, re.IGNORECASE) or \
                                     re.search(r"\*\*Leeftijdsbereik:?\*\*\s*(\d+)\+", spec_text, re.IGNORECASE)
                    if age_range_match:
                        try:
                            specs["age_range"] = f"{age_range_match.group(1)}+"
                            specs["min_age"] = int(age_range_match.group(1))
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract dimensions - try different patterns
                    dimensions_match = re.search(r"Dimensions:?\s*([^-\n]+)", spec_text, re.IGNORECASE) or \
                                      re.search(r"\*\*Dimensions:?\*\*\s*([^-\n]+)", spec_text, re.IGNORECASE)
                    if dimensions_match:
                        specs["dimensions"] = dimensions_match.group(1).strip()
                    
                    # Extract set number - try different patterns
                    set_number_match = re.search(r"Set Number:?\s*(\d+)", spec_text, re.IGNORECASE) or \
                                      re.search(r"\*\*Set Number:?\*\*\s*(\d+)", spec_text, re.IGNORECASE) or \
                                      re.search(r"\*\*Setnummer:?\*\*\s*(\d+)", spec_text, re.IGNORECASE)
                    if set_number_match:
                        set_number = set_number_match.group(1)
                        if not correct_product_id:
                            correct_product_id = set_number
                            product_info["id"] = set_number
                    
                    # Extract theme - try different patterns
                    theme_match = re.search(r"Theme:?\s*([^\n]+)", spec_text, re.IGNORECASE) or \
                                 re.search(r"\*\*Theme:?\*\*\s*([^\n]+)", spec_text, re.IGNORECASE) or \
                                 re.search(r"\*\*Thema:?\*\*\s*([^\n]+)", spec_text, re.IGNORECASE)
                    if theme_match:
                        theme = theme_match.group(1).strip()
                        # Remove any markdown formatting
                        theme = re.sub(r'\*\*', '', theme)
                        specs["theme"] = theme
                
                # Try to extract from English description and features
                if "en" in markdown_content:
                    all_text = ""
                    if "description" in markdown_content["en"]:
                        all_text += markdown_content["en"]["description"] + "\n"
                    if "features" in markdown_content["en"]:
                        all_text += markdown_content["en"]["features"] + "\n"
                    
                    # Extract minifigures
                    minifig_match = re.search(r"Includes\s+(\d+)\s+minifigures?", all_text, re.IGNORECASE) or \
                                   re.search(r"with\s+(\d+)\s+minifigures?", all_text, re.IGNORECASE) or \
                                   re.search(r"(\d+)\s+minifigures?", all_text, re.IGNORECASE)
                    if minifig_match:
                        try:
                            specs["minifigures"] = int(minifig_match.group(1))
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract minifigure names - improved pattern
                    minifig_names_match = re.search(r"minifigures?:?\s*([\w\s,]+(?:and|&)[\w\s]+)", all_text, re.IGNORECASE) or \
                                         re.search(r"Includes\s+\d+\s+minifigures?:?\s*([\w\s,]+(?:and|&)[\w\s]+)", all_text, re.IGNORECASE) or \
                                         re.search(r"minifigures?:?\s*([\w\s,]+)", all_text, re.IGNORECASE)
                    
                    if minifig_names_match:
                        minifig_names = minifig_names_match.group(1).strip()
                        # Clean up the names
                        minifig_names = re.sub(r'[!,]', ' ', minifig_names)
                        minifig_names = re.sub(r'\s+', ' ', minifig_names)
                        minifig_names = re.sub(r'^\s*-\s*', '', minifig_names)  # Remove leading dash
                        
                        # Special handling for "and more" or similar phrases
                        if "and more" in minifig_names.lower():
                            # Keep the "and more" phrase as it indicates additional unnamed minifigures
                            pass
                        
                        specs["minifigure_names"] = minifig_names
                    
                    # Extract dimensions from all text
                    dimensions_match = re.search(r"dimensions:?\s*([^\.]+)", all_text, re.IGNORECASE) or \
                                      re.search(r"measures\s+([^\.]+)", all_text, re.IGNORECASE) or \
                                      re.search(r"(\d+\s*cm\s*[xX×]\s*\d+\s*cm\s*[xX×]\s*\d+\s*cm)", all_text, re.IGNORECASE)
                    if dimensions_match:
                        specs["dimensions"] = dimensions_match.group(1).strip()
                
                # Try to extract from Dutch description and features
                if "nl" in markdown_content:
                    all_text = ""
                    if "description" in markdown_content["nl"]:
                        all_text += markdown_content["nl"]["description"] + "\n"
                    if "features" in markdown_content["nl"]:
                        all_text += markdown_content["nl"]["features"] + "\n"
                    
                    # Extract minifigures from Dutch text if not already found
                    if "minifigures" not in specs:
                        minifig_match = re.search(r"Inclusief\s+(\d+)\s+minifigur(en|es)?", all_text, re.IGNORECASE) or \
                                       re.search(r"met\s+(\d+)\s+minifigur(en|es)?", all_text, re.IGNORECASE) or \
                                       re.search(r"(\d+)\s+minifigur(en|es)?", all_text, re.IGNORECASE)
                        if minifig_match:
                            try:
                                specs["minifigures"] = int(minifig_match.group(1))
                            except (ValueError, TypeError):
                                pass
                    
                    # Extract minifigure names from Dutch text if not already found
                    if "minifigure_names" not in specs:
                        minifig_names_match = re.search(r"minifigur(?:en|es)?:?\s*([\w\s,]+(?:en|&)[\w\s]+)", all_text, re.IGNORECASE) or \
                                             re.search(r"Inclusief\s+\d+\s+minifigur(?:en|es)?:?\s*([\w\s,]+(?:en|&)[\w\s]+)", all_text, re.IGNORECASE)
                        
                        if minifig_names_match:
                            minifig_names = minifig_names_match.group(1).strip()
                            # Clean up the names
                            minifig_names = re.sub(r'[!,]', ' ', minifig_names)
                            minifig_names = re.sub(r'\s+', ' ', minifig_names)
                            specs["minifigure_names"] = minifig_names
                    
                    # Extract dimensions from Dutch text if not already found
                    if "dimensions" not in specs:
                        dimensions_match = re.search(r"afmetingen:?\s*([^\.]+)", all_text, re.IGNORECASE) or \
                                          re.search(r"meet\s+([^\.]+)", all_text, re.IGNORECASE) or \
                                          re.search(r"(\d+\s*cm\s*[xX×]\s*\d+\s*cm\s*[xX×]\s*\d+\s*cm)", all_text, re.IGNORECASE)
                        if dimensions_match:
                            specs["dimensions"] = dimensions_match.group(1).strip()
            
            # NEW: Try to extract minifigure information from raw data
            if isinstance(raw_data, dict):
                raw_data_str = json.dumps(raw_data)
                
                # Special handling for NINJAGO City Workshops (71837)
                if product_info["id"] == "71837":
                    # Try to find the detailed minifigure list in the description
                    ninjago_minifigs_match = re.search(r'De set bevat 10 NINJAGO minifiguren: ([^<]+)', raw_data_str)
                    if ninjago_minifigs_match:
                        minifig_text = ninjago_minifigs_match.group(1)
                        # Clean up the text
                        minifig_text = minifig_text.replace('\\n', ' ').replace('\\', '')
                        minifig_text = re.sub(r'\s+', ' ', minifig_text)
                        
                        # Extract just the minifigure names without the additional text
                        end_idx = minifig_text.find('. Fans kunnen')
                        if end_idx > 0:
                            minifig_text = minifig_text[:end_idx]
                        
                        # Further clean up the text to make it more concise
                        minifig_text = minifig_text.replace('een modelwinkeleigenaar', 'modelwinkeleigenaar')
                        minifig_text = minifig_text.replace('een werkplaatsmonteur', 'werkplaatsmonteur')
                        minifig_text = minifig_text.replace('een restaurantmedewerker', 'restaurantmedewerker')
                        minifig_text = minifig_text.replace('een Draconische toerist', 'Draconische toerist')
                        minifig_text = minifig_text.replace('plus niet eerder uitgebrachte minifiguren van', 'plus')
                        minifig_text = minifig_text.replace('en een bouwbare figuur van', 'en')
                        minifig_text = re.sub(r'\s+', ' ', minifig_text)
                        minifig_text = minifig_text.strip()
                        
                        # Fix any double commas or formatting issues
                        minifig_text = re.sub(r',\s*,', ',', minifig_text)
                        minifig_text = re.sub(r',\s*plus', ' plus', minifig_text)
                        minifig_text = re.sub(r',\s*en', ' en', minifig_text)
                        
                        specs["minifigure_names"] = minifig_text
                    
                    # Extract dimensions
                    dimensions_match = re.search(r'Afmetingen – deze NINJAGO® City werkplaatsen bouwset met \d+ onderdelen is ca\. ([^<]+)', raw_data_str) or \
                                      re.search(r'ca\. 41 cm hoog, 25 cm breed en 25 cm diep', raw_data_str)
                    if dimensions_match:
                        if dimensions_match.groups():
                            dimensions = dimensions_match.group(1).strip()
                        else:
                            dimensions = "41 cm hoog, 25 cm breed en 25 cm diep"
                        specs["dimensions"] = dimensions
                
                # Look for "Met alle sterren" section which might contain minifigure info
                elif "Met alle sterren" in raw_data_str and "minifigure_names" in specs:
                    # If we already have minifigure names but they contain "and more", try to find more specific names
                    if "and more" in specs["minifigure_names"].lower() or "en meer" in specs["minifigure_names"].lower():
                        # Try to find more specific minifigure names in the raw data
                        ninja_names = ["Lloyd", "Nya", "Kai", "Jay", "Cole", "Zane", "Wu", "Garmadon"]
                        found_names = []
                        
                        for name in ninja_names:
                            if re.search(r'\b' + re.escape(name) + r'\b', raw_data_str, re.IGNORECASE):
                                found_names.append(name)
                        
                        if found_names:
                            # If we found specific names, update the minifigure_names
                            if len(found_names) < specs.get("minifigures", 10):
                                # If we found fewer names than the total minifigures, add "and more"
                                specs["minifigure_names"] = ", ".join(found_names) + " and more"
                            else:
                                specs["minifigure_names"] = ", ".join(found_names)
            
            # Add specifications if we found any
            if specs:
                product_info["specs"] = specs
            
            # Extract description
            if "meta_tags" in raw_data and "description" in raw_data["meta_tags"]:
                product_info["description"] = raw_data["meta_tags"]["description"]
            
            # Extract condition
            if "meta_tags" in raw_data and "product:condition" in raw_data["meta_tags"]:
                product_info["condition"] = raw_data["meta_tags"]["product:condition"]
            
            # NEW: Extract rich text content for SEO purposes
            if isinstance(raw_data, dict):
                raw_data_str = json.dumps(raw_data)
                
                # Extract detailed description
                description_match = re.search(r'"description":\s*"([^"]+)"', raw_data_str)
                if description_match:
                    detailed_description = description_match.group(1)
                    # Clean up the text
                    detailed_description = detailed_description.replace('\\n', '\n').replace('\\\\', '\\')
                    detailed_description = re.sub(r'<[^>]+>', ' ', detailed_description)  # Remove HTML tags
                    detailed_description = re.sub(r'\s+', ' ', detailed_description).strip()
                    detailed_description = html.unescape(detailed_description)  # Handle HTML entities
                    
                    # Fix common encoding issues
                    detailed_description = detailed_description.replace('\\u00ae', '®')
                    detailed_description = detailed_description.replace('\\u2013', '-')
                    detailed_description = detailed_description.replace('\\u2019', "'")
                    
                    if "seo_content" not in product_info:
                        product_info["seo_content"] = {}
                    
                    product_info["seo_content"]["detailed_description"] = detailed_description
                
                # Extract features text
                features_match = re.search(r'"featuresText":\s*"([^"]+)"', raw_data_str)
                if features_match:
                    features_text = features_match.group(1)
                    # Clean up the text
                    features_text = features_text.replace('\\n', '\n').replace('\\\\', '\\')
                    
                    # Extract bullet points for features before removing HTML tags
                    bullet_points = []
                    bullet_match = re.search(r'<ul>(.*?)</ul>', features_text)
                    if bullet_match:
                        bullet_html = bullet_match.group(1)
                        bullet_items = re.findall(r'<li>(.*?)</li>', bullet_html)
                        for item in bullet_items:
                            # Clean up the text
                            clean_item = re.sub(r'<[^>]+>', ' ', item)
                            clean_item = re.sub(r'\s+', ' ', clean_item).strip()
                            clean_item = html.unescape(clean_item)  # Handle HTML entities
                            
                            # Fix common encoding issues
                            clean_item = clean_item.replace('\\u00ae', '®')
                            clean_item = clean_item.replace('\\u2013', '-')
                            clean_item = clean_item.replace('\\u2019', "'")
                            
                            bullet_points.append(clean_item)
                    
                    # Now clean the full features text
                    features_text = re.sub(r'<[^>]+>', ' ', features_text)  # Remove HTML tags
                    features_text = re.sub(r'\s+', ' ', features_text).strip()
                    features_text = html.unescape(features_text)  # Handle HTML entities
                    
                    # Fix common encoding issues
                    features_text = features_text.replace('\\u00ae', '®')
                    features_text = features_text.replace('\\u2013', '-')
                    features_text = features_text.replace('\\u2019', "'")
                    
                    if "seo_content" not in product_info:
                        product_info["seo_content"] = {}
                    
                    product_info["seo_content"]["features_text"] = features_text
                    
                    if bullet_points:
                        product_info["seo_content"]["feature_bullets"] = bullet_points
            
            # Update product data with enhanced information
            product_data["product"] = product_info
            
            # Remove old enhanced_data if it exists
            if "enhanced_data" in product_data:
                del product_data["enhanced_data"]
            
            # Save updated product data
            if "product" in product_data:
                product_data["product"] = product_info
                with open(product_path, "w") as f:
                    json.dump(product_data, f, indent=2)
            else:
                with open(product_path, "w") as f:
                    json.dump(product_info, f, indent=2)
            
            print(f"Product data updated with Cloudflare URLs and saved to {product_path}")
        
        except Exception as e:
            print(f"Error processing {raw_file}: {str(e)}")
    
    print("Data extraction complete")

def generate_seo_content(product_id: str) -> Dict[str, str]:
    """Generate SEO-optimized content for a product based on extracted data.
    
    Args:
        product_id: The LEGO product ID
        
    Returns:
        Dictionary with SEO content including meta title, meta description, and product description
    """
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return {}
    
    # Load product data
    with open(product_path, 'r', encoding='utf-8') as f:
        product_data = json.load(f)
    
    product_info = product_data.get("product", {})
    seo_content = product_info.get("seo_content", {})
    specs = product_info.get("specs", {})
    
    # Extract key information
    title = product_info.get("title", "").split("|")[0].strip()
    piece_count = specs.get("piece_count", "")
    age_range = specs.get("age_range", "")
    theme = specs.get("theme", "").strip()
    price = product_info.get("price", {}).get("amount", "")
    currency = product_info.get("price", {}).get("currency", "EUR")
    minifigures = specs.get("minifigures", "")
    minifigure_names = specs.get("minifigure_names", "")
    dimensions = specs.get("dimensions", "")
    
    # Generate SEO content
    seo_output = {}
    
    # Meta title (50-60 characters)
    seo_output["meta_title"] = f"{title} ({product_id}) - {piece_count} Pieces - {theme}"
    if len(seo_output["meta_title"]) > 60:
        seo_output["meta_title"] = f"{title} ({product_id}) - {theme}"
    
    # Meta description (150-160 characters)
    meta_desc = f"Build the {title} LEGO® set with {piece_count} pieces"
    if minifigures:
        meta_desc += f", {minifigures} minifigures"
    if price:
        meta_desc += f", {price} {currency}"
    meta_desc += f". {age_range} age range. Official LEGO® set."
    
    seo_output["meta_description"] = meta_desc[:160]
    
    # Product short description (for category pages)
    short_desc = f"The {title} ({product_id}) is a {piece_count}-piece LEGO® {theme} set"
    if minifigures:
        short_desc += f" featuring {minifigures} minifigures"
    if dimensions:
        short_desc += f". When built, it measures {dimensions}"
    short_desc += "."
    
    seo_output["short_description"] = short_desc
    
    # Full product description (for product pages)
    full_desc = []
    
    # Intro paragraph
    if "detailed_description" in seo_content:
        full_desc.append(seo_content["detailed_description"])
    else:
        full_desc.append(f"The {title} is an impressive {piece_count}-piece LEGO® {theme} set designed for builders {age_range}.")
    
    # Main description from features text
    if "features_text" in seo_content:
        # Take first 2-3 sentences from features text
        sentences = seo_content["features_text"].split('. ')
        main_desc = '. '.join(sentences[:3]) + '.'
        full_desc.append(main_desc)
    
    # Feature bullets
    if "feature_bullets" in seo_content and seo_content["feature_bullets"]:
        full_desc.append("\nKey Features:")
        for bullet in seo_content["feature_bullets"][:5]:  # Limit to top 5 features
            full_desc.append(f"• {bullet}")
    
    # Specifications
    full_desc.append("\nSpecifications:")
    full_desc.append(f"• Product Number: {product_id}")
    full_desc.append(f"• Piece Count: {piece_count}")
    full_desc.append(f"• Age Recommendation: {age_range}")
    if dimensions:
        full_desc.append(f"• Dimensions: {dimensions}")
    if minifigures:
        full_desc.append(f"• Includes {minifigures} minifigures: {minifigure_names}")
    
    # Call to action
    full_desc.append("\nAdd this amazing LEGO® set to your collection today!")
    
    seo_output["full_description"] = "\n".join(full_desc)
    
    return seo_output

def generate_seo_articles(product_id: str, language: str = "en", save_prompt_only: bool = False) -> Dict[str, str]:
    """Generate SEO-optimized articles for a product using DeepSeek.
    
    Args:
        product_id: The LEGO product ID
        language: The language to generate the article in ('en' for English, 'nl' for Dutch)
        save_prompt_only: If True, only save the prompt without calling the API
        
    Returns:
        Dictionary containing the generated article content
    """
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    prompt_path = os.path.join("input", "article-prompt.md")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return {"error": "Product file not found"}
    
    if not os.path.exists(prompt_path):
        print(f"Article prompt template not found: {prompt_path}")
        return {"error": "Article prompt template not found"}
    
    # Load product data
    with open(product_path, 'r', encoding='utf-8') as f:
        product_data = json.load(f)
    
    # Load article prompt template
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # Extract product information
    product_info = product_data.get("product", {})
    content = product_data.get("content", {}).get("markdown", {})
    metadata = product_data.get("metadata", {})
    
    # Select language-specific content
    lang_content = content.get(language, content.get("en", {}))
    
    # Prepare product data for the prompt
    seo_content = product_info.get("seo_content", {})
    
    # Create a simplified product data structure for the prompt
    prompt_product_data = {
        "content": {
            "markdown": {
                "en": {
                    "title": lang_content.get("title", product_info.get("title", "")),
                    "description": lang_content.get("description", ""),
                    "features": lang_content.get("features", ""),
                    "specifications": lang_content.get("specifications", "")
                }
            },
            "metadata": {
                "product_id": product_info.get("id", ""),
                "price": product_info.get("price", {"amount": 0, "currency": "EUR"}),
                "availability": product_info.get("status", "unknown"),
                "brand": "LEGO®",
                "condition": product_info.get("condition", "new")
            }
        },
        "product": {
            "specs": product_info.get("specs", {}),
            "images": product_info.get("images", [])[:5]  # Limit to 5 images to keep prompt size reasonable
        }
    }
    
    # Create the complete prompt
    seo_content_json = json.dumps(seo_content, indent=2)
    
    # Find the position of the SEO content in the template
    seo_content_start = prompt_template.find('```json\n"seo_content":')
    seo_content_end = prompt_template.find('```', seo_content_start + 10)
    
    if seo_content_start != -1 and seo_content_end != -1:
        # Replace the SEO content section
        prompt = (
            prompt_template[:seo_content_start] + 
            f'```json\n"seo_content": {seo_content_json}\n' + 
            prompt_template[seo_content_end:]
        )
    else:
        # Fallback if we can't find the exact position
        prompt = prompt_template
    
    # Replace the product data placeholder
    product_data_start = prompt.find('```json\n{\n  "content":')
    product_data_end = prompt.find('```', product_data_start + 10)
    
    if product_data_start != -1 and product_data_end != -1:
        # Replace the product data section
        prompt_product_data_json = json.dumps(prompt_product_data, indent=2)
        prompt = (
            prompt[:product_data_start] + 
            f'```json\n{prompt_product_data_json}\n' + 
            prompt[product_data_end:]
        )
    
    # Save the prompt for manual submission if needed
    prompt_dir = os.path.join(ARTICLES_DIR, "prompts")
    os.makedirs(prompt_dir, exist_ok=True)
    prompt_file = os.path.join(prompt_dir, f"prompt_{product_id}_{language}.txt")
    
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"Saved prompt to {prompt_file}")
    
    if save_prompt_only:
        return {
            "success": True,
            "prompt_path": prompt_file,
            "message": "Prompt saved for manual submission"
        }
    
    # Call DeepSeek API to generate the article
    try:
        # Load DeepSeek API key directly from .env file
        api_key = None
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DEEPSEEK_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        break
        except Exception as e:
            print(f"Error reading .env file: {str(e)}")
        
        if not api_key:
            print("DeepSeek API key not found in .env file")
            return {
                "error": "DeepSeek API key not found",
                "prompt_path": prompt_file,
                "message": "Prompt saved for manual submission"
            }
        
        # Debug: Print the API key (first 5 and last 5 characters)
        if len(api_key) > 10:
            masked_key = f"{api_key[:5]}...{api_key[-5:]}"
        else:
            masked_key = "Invalid key format"
        print(f"Calling DeepSeek API with API key: {masked_key}")
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": f"You are an expert SEO content writer specializing in LEGO products. Your task is to create a comprehensive, SEO-optimized article about a LEGO product in {language.upper()} language."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        # Make API request
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        
        # Extract and save the generated article
        result = response.json()
        article_content = result["choices"][0]["message"]["content"]
        
        # Save the article
        article_path = os.path.join(ARTICLES_DIR, f"article_{product_id}_{language}.md")
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(article_content)
        
        print(f"Generated SEO article saved to {article_path}")
        
        return {
            "success": True,
            "article_path": article_path,
            "article_content": article_content
        }
    
    except Exception as e:
        print(f"Error generating SEO article: {str(e)}")
        return {
            "error": str(e),
            "prompt_path": prompt_file,
            "message": "Prompt saved for manual submission"
        }

def create_seo_filename(image_url: str, product_id: str, is_high_res: bool = False) -> str:
    """Create an SEO-friendly filename for an image.
    
    Args:
        image_url: The URL of the image
        product_id: The LEGO product ID
        is_high_res: Whether this is a high-resolution image
        
    Returns:
        An SEO-friendly filename
    """
    # Parse the URL
    parsed_url = urlparse(image_url)
    path = unquote(parsed_url.path)
    
    # Load the product data to get the title
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    if os.path.exists(product_path):
        with open(product_path, "r") as f:
            product_info = json.load(f)
        
        # Get product title for SEO-friendly filenames
        product_title = product_info.get("title", "").split("|")[0].strip()
        product_title = re.sub(r'[^\w\s-]', '', product_title).strip().lower()
        product_title = re.sub(r'[\s]+', '-', product_title)
    else:
        product_title = f"lego-set-{product_id}"
    
    # Determine image type
    image_type = "product"
    if "boxprod" in path:
        image_type = "box"
    elif "lifestyle" in path:
        image_type = "lifestyle"
    elif "WEB_SEC" in path:
        # Extract the section number if available
        match = re.search(r'WEB_SEC(\d+)', path)
        if match:
            section_num = match.group(1)
            image_type = f"detail-{section_num}"
        else:
            # If no section number, use a generic detail name
            image_type = "detail"
    
    # Determine file extension
    if path.lower().endswith('.jpg') or path.lower().endswith('.jpeg') or 'format=jpg' in image_url:
        ext = ".jpg"
    else:
        ext = ".png"
    
    # Create the filename
    if is_high_res:
        filename = f"lego-{product_id}-{product_title}-{image_type}-high-res{ext}"
    else:
        filename = f"lego-{product_id}-{product_title}-{image_type}{ext}"
    
    # Clean up the filename
    filename = filename.replace("--", "-").replace("--", "-")
    
    return filename

def download_image(url: str, local_path: str) -> None:
    """Download an image from a URL and save it to a local path.
    
    Args:
        url: The URL of the image
        local_path: The local path to save the image to
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        raise Exception(f"Error downloading image: {str(e)}")

def optimize_images(product_id: str, upload_to_cloudflare: bool = False) -> Dict[str, Any]:
    """Download images for a product and upload them to Cloudflare R2.
    
    Instead of local optimization, we'll let Cloudflare handle image optimization.
    
    Args:
        product_id: The LEGO product ID
        upload_to_cloudflare: Whether to upload images to Cloudflare R2
        
    Returns:
        Dictionary containing information about the processed images
    """
    setup_directories()
    
    # Check if boto3 is available
    boto3_available = False
    try:
        import boto3
        boto3_available = True
        print("boto3 is available, Cloudflare R2 upload functionality is enabled")
    except ImportError:
        print("boto3 is not installed, Cloudflare R2 upload functionality is disabled")
        upload_to_cloudflare = False
    
    # Load environment variables
    load_dotenv()
    
    # Check if Cloudflare credentials are available
    cloudflare_credentials_available = all([
        os.getenv("CLOUDFLARE_ACCESS_KEY_ID"),
        os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY"),
        os.getenv("CLOUDFLARE_ACCOUNT_ID"),
        os.getenv("CLOUDFLARE_R2_BUCKET"),
        os.getenv("CLOUDFLARE_DOMAIN")
    ])
    
    if not cloudflare_credentials_available:
        print("Cloudflare credentials are not available, Cloudflare R2 upload functionality is disabled")
        print(f"CLOUDFLARE_ACCESS_KEY_ID: {'Available' if os.getenv('CLOUDFLARE_ACCESS_KEY_ID') else 'Missing'}")
        print(f"CLOUDFLARE_SECRET_ACCESS_KEY: {'Available' if os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY') else 'Missing'}")
        print(f"CLOUDFLARE_ACCOUNT_ID: {'Available' if os.getenv('CLOUDFLARE_ACCOUNT_ID') else 'Missing'}")
        print(f"CLOUDFLARE_R2_BUCKET: {'Available' if os.getenv('CLOUDFLARE_R2_BUCKET') else 'Missing'}")
        print(f"CLOUDFLARE_DOMAIN: {'Available' if os.getenv('CLOUDFLARE_DOMAIN') else 'Missing'}")
        upload_to_cloudflare = False
    
    # Only enable Cloudflare upload if boto3 is available and credentials are set
    upload_to_cloudflare = upload_to_cloudflare and boto3_available and cloudflare_credentials_available
    
    if upload_to_cloudflare:
        print("Cloudflare R2 upload functionality is enabled")
    else:
        print("Cloudflare R2 upload functionality is disabled")
    
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return {"error": "Product file not found"}
    
    # Load the product data
    with open(product_path, "r") as f:
        product_data = json.load(f)
    
    print(f"Product data loaded from {product_path}")
    print(f"Product data keys: {list(product_data.keys())}")
    
    # Extract the product info from the nested structure if needed
    if "product" in product_data:
        product_info = product_data["product"]
        print("Using nested product data structure")
    else:
        product_info = product_data
        print("Using flat product data structure")
    
    # Check if we have image data
    if "image" in product_info:
        print(f"Found main image: {product_info['image']}")
    else:
        print("No main image found in product data")
    
    if "images" in product_info:
        print(f"Found images array with {len(product_info['images'])} images")
    else:
        print("No images array found in product data")
    
    # Create output directory
    output_dir = os.path.join(IMAGES_DIR, product_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize variables
    downloaded_images = []
    image_mapping = {}
    downloaded_count = 0
    high_res_downloaded_count = 0
    
    # Extract image URLs from product data
    image_urls = []
    high_res_image_urls = []
    
    # Add main image
    if "image" in product_info:
        print(f"Found main image: {product_info['image']}")
        image_urls.append(product_info["image"])
    
    # Add high-res main image
    if "high_res_image" in product_info:
        print(f"Found high-res main image: {product_info['high_res_image']}")
        high_res_image_urls.append(product_info["high_res_image"])
    
    # Add images array
    if "images" in product_info:
        print(f"Found {len(product_info['images'])} images in the images array")
        for img_url in product_info["images"]:
            if img_url not in image_urls:
                image_urls.append(img_url)
    
    # Add high-res images array
    if "high_res_images" in product_info:
        print(f"Found {len(product_info['high_res_images'])} images in the high_res_images array")
        for img_url in product_info["high_res_images"]:
            if img_url not in high_res_image_urls:
                high_res_image_urls.append(img_url)
    
    print(f"Total standard images to process: {len(image_urls)}")
    print(f"Total high-res images to process: {len(high_res_image_urls)}")
    
    # Download standard images
    for image_url in image_urls:
        try:
            # Create SEO-friendly filename
            filename = create_seo_filename(image_url, product_id)
            local_path = os.path.join(output_dir, filename)
            
            # Download the image if it doesn't exist
            if not os.path.exists(local_path):
                print(f"Downloading image: {filename}")
                download_image(image_url, local_path)
                downloaded_count += 1
                print(f"Downloaded image: {filename}")
            else:
                print(f"Image already exists: {filename}")
            
            # Add to downloaded images list
            downloaded_images.append({
                "original_url": image_url,
                "local_path": local_path,
                "seo_filename": filename,
                "is_high_res": False
            })
            
            # Add to image mapping
            image_mapping[image_url] = {
                "local_path": local_path,
                "seo_filename": filename,
                "cloudflare_url": f"https://{os.getenv('CLOUDFLARE_DOMAIN')}/{product_id}/{filename}"
            }
        except Exception as e:
            print(f"Error downloading image {image_url}: {str(e)}")
    
    # Download high-res images
    for high_res_image_url in high_res_image_urls:
        try:
            # Create SEO-friendly filename
            filename = create_seo_filename(high_res_image_url, product_id, is_high_res=True)
            local_path = os.path.join(output_dir, filename)
            
            # Download the image if it doesn't exist
            if not os.path.exists(local_path):
                print(f"Downloading high-res image: {filename}")
                download_image(high_res_image_url, local_path)
                high_res_downloaded_count += 1
                print(f"Downloaded high-res image: {filename}")
            else:
                print(f"High-res image already exists: {filename}")
            
            # Add to downloaded images list
            downloaded_images.append({
                "original_url": high_res_image_url,
                "local_path": local_path,
                "seo_filename": filename,
                "is_high_res": True
            })
            
            # Add to image mapping
            image_mapping[high_res_image_url] = {
                "local_path": local_path,
                "seo_filename": filename,
                "cloudflare_url": f"https://{os.getenv('CLOUDFLARE_DOMAIN')}/{product_id}/{filename}"
            }
        except Exception as e:
            print(f"Error downloading high-res image {high_res_image_url}: {str(e)}")
    
    # Save the image mapping
    with open(os.path.join(output_dir, "image_mapping.json"), "w") as f:
        json.dump(image_mapping, f, indent=2)
    
    # Upload images to Cloudflare R2 if requested
    if upload_to_cloudflare and image_mapping:
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Set up Cloudflare R2 client
            cloudflare_endpoint = f"https://{os.getenv('CLOUDFLARE_ACCOUNT_ID')}.r2.cloudflarestorage.com"
            s3_client = boto3.client(
                's3',
                endpoint_url=cloudflare_endpoint,
                aws_access_key_id=os.getenv('CLOUDFLARE_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('CLOUDFLARE_SECRET_ACCESS_KEY')
            )
            
            bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET')
            cloudflare_domain = os.getenv('CLOUDFLARE_DOMAIN')
            
            print(f"Connecting to Cloudflare R2 at endpoint: {cloudflare_endpoint}")
            print(f"Using bucket: {bucket_name}")
            
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                print(f"Bucket {bucket_name} exists")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code == '404':
                    print(f"Bucket {bucket_name} does not exist, creating it...")
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    print(f"Error checking bucket: {str(e)}")
                    return {"error": f"Error checking bucket: {str(e)}"}
            
            # Upload each image to Cloudflare R2
            for original_url, image_info in image_mapping.items():
                local_path = image_info["local_path"]
                seo_filename = image_info["seo_filename"]
                
                # Create the object key (path in the bucket)
                object_key = f"{product_id}/{seo_filename}"
                
                # Set the Cloudflare URL
                cloudflare_url = f"https://{cloudflare_domain}/{object_key}"
                image_info["cloudflare_url"] = cloudflare_url
                
                try:
                    print(f"Uploading {local_path} to {object_key}...")
                    
                    # Determine content type based on file extension
                    content_type = "image/jpeg" if local_path.endswith(".jpg") else "image/png"
                    
                    # Upload the file
                    with open(local_path, 'rb') as file:
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=object_key,
                            Body=file,
                            ContentType=content_type,
                            CacheControl="max-age=31536000"  # Cache for 1 year
                        )
                    print(f"Successfully uploaded {seo_filename} to Cloudflare R2")
                except Exception as e:
                    print(f"Error uploading {seo_filename} to Cloudflare R2: {str(e)}")
            
            # Save the updated image mapping
            with open(os.path.join(output_dir, "image_mapping.json"), "w") as f:
                json.dump(image_mapping, f, indent=2)
            
            # Update the product data with Cloudflare URLs
            print("Updating product data with Cloudflare URLs...")
            
            # Update the main image
            if "image" in product_info and product_info["image"] in image_mapping:
                print(f"Updating main image URL to {image_mapping[product_info['image']]['cloudflare_url']}")
                product_info["image"] = image_mapping[product_info["image"]]["cloudflare_url"]
            
            # Update the high-res image
            if "high_res_image" in product_info and product_info["high_res_image"] in image_mapping:
                print(f"Updating high-res image URL to {image_mapping[product_info['high_res_image']]['cloudflare_url']}")
                product_info["high_res_image"] = image_mapping[product_info["high_res_image"]]["cloudflare_url"]
            
            # Update the images array
            if "images" in product_info:
                updated_images = []
                for img_url in product_info["images"]:
                    if img_url in image_mapping:
                        print(f"Updating image URL in images array to {image_mapping[img_url]['cloudflare_url']}")
                        updated_images.append(image_mapping[img_url]["cloudflare_url"])
                    else:
                        updated_images.append(img_url)
                product_info["images"] = updated_images
            
            # Update the high-res images array
            if "high_res_images" in product_info:
                updated_high_res_images = []
                for img_url in product_info["high_res_images"]:
                    if img_url in image_mapping:
                        print(f"Updating high-res image URL in high_res_images array to {image_mapping[img_url]['cloudflare_url']}")
                        updated_high_res_images.append(image_mapping[img_url]["cloudflare_url"])
                    else:
                        updated_high_res_images.append(img_url)
                product_info["high_res_images"] = updated_high_res_images
            
            # Save the updated product data
            if "product" in product_data:
                product_data["product"] = product_info
                with open(product_path, "w") as f:
                    json.dump(product_data, f, indent=2)
            else:
                with open(product_path, "w") as f:
                    json.dump(product_info, f, indent=2)
            
            print(f"Product data updated with Cloudflare URLs and saved to {product_path}")
        
        except Exception as e:
            print(f"Error uploading images to Cloudflare R2: {str(e)}")
    
    return {
        "product_id": product_id,
        "images_dir": output_dir,
        "image_mapping": image_mapping,
        "downloaded_count": downloaded_count,
        "high_res_downloaded_count": high_res_downloaded_count,
        "optimized_count": len(image_mapping),
        "high_res_optimized_count": len([k for k in image_mapping.keys() if 'high_res' in k or 'dpr=2' in k])
    }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="LEGO Scraper Workflow")
    
    # Add arguments
    parser.add_argument("--scrape", action="store_true", help="Scrape new products")
    parser.add_argument("--max-pages", type=int, help="Maximum number of pages to scrape")
    parser.add_argument("--process-urls", action="store_true", help="Process URLs from the input file")
    parser.add_argument("--max-workers", type=int, default=3, help="Maximum number of workers for processing URLs")
    parser.add_argument("--use-proxies", action="store_true", help="Use proxies for processing URLs")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for processing URLs")
    parser.add_argument("--analyze", action="store_true", help="Analyze raw data")
    parser.add_argument("--extract-data", action="store_true", help="Extract additional data from raw data")
    parser.add_argument("--generate-seo", type=str, help="Generate SEO content for a product ID")
    parser.add_argument("--generate-article", type=str, help="Generate SEO article for a product ID")
    parser.add_argument("--language", type=str, default="en", help="Language for article generation (en or nl)")
    parser.add_argument("--save-prompt-only", action="store_true", help="Save the prompt without calling the API")
    parser.add_argument("--optimize-images", type=str, help="Optimize images for a product ID")
    parser.add_argument("--upload-to-cloudflare", action="store_true", help="Upload optimized images to Cloudflare R2")
    parser.add_argument("--list-processed", action="store_true", help="List processed URLs")
    
    args = parser.parse_args()
    
    # Ensure all directories exist
    setup_directories()
    
    if args.scrape:
        scrape_new_products(args.max_pages)
    
    if args.process_urls:
        process_urls(args.max_workers, args.use_proxies, args.timeout)
    
    if args.analyze:
        analyze_raw_data()
    
    if args.extract_data:
        extract_additional_data()
    
    if args.generate_seo:
        result = generate_seo_content(args.generate_seo)
        print(f"SEO content generated for product {args.generate_seo}")
        print(f"Title: {result['title']}")
        print(f"Meta Description: {result['meta_description']}")
    
    if args.generate_article:
        result = generate_seo_articles(args.generate_article, args.language, args.save_prompt_only)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Article generated for product {args.generate_article} in {args.language}")
            if args.save_prompt_only:
                print(f"Prompt saved to: {result['prompt_path']}")
            else:
                print(f"Article saved to: {result['article_path']}")
    
    if args.optimize_images:
        result = optimize_images(args.optimize_images, args.upload_to_cloudflare)
        print(f"Images for product {args.optimize_images} optimized and saved to {result['images_dir']}")
        print(f"Downloaded {result['downloaded_count']} images ({result['high_res_downloaded_count']} high-res)")
        print(f"Successfully optimized {result['optimized_count']} images ({result['high_res_optimized_count']} high-res)")
        print(f"Images saved to: {result['images_dir']}")
        print(f"Image mapping saved to: {os.path.join(result['images_dir'], 'image_mapping.json')}")
    
    if args.list_processed:
        processed_urls = list_processed_urls()
        print(f"Found {len(processed_urls)} processed URLs:")
        for url_info in processed_urls:
            print(f"URL: {url_info['url']}")
            print(f"  Product ID: {url_info['product_id']}")
            print(f"  Last Processed: {url_info['timestamp']}")
            print()

if __name__ == "__main__":
    main() 