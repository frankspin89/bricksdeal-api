#!/usr/bin/env python3

import os
import json
import sqlite3
import argparse
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import re
import shutil

# Constants
DATABASE_FILE = os.path.join("output", "lego_database.sqlite")
PRODUCTS_DIR = os.path.join("output", "products")
IMAGES_DIR = os.path.join("output", "images")

def ensure_directories():
    """Ensure all necessary directories exist."""
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

def normalize_set_id(set_id: str) -> str:
    """Normalize a set ID to ensure consistent format."""
    if not set_id:
        return set_id
    
    # If the set ID doesn't have a dash, add -1 suffix
    if "-" not in set_id:
        return f"{set_id}-1"
    
    return set_id

def find_matching_catalog_id(scraped_id: str, cursor) -> Optional[str]:
    """Find a matching catalog ID for a scraped ID."""
    # Try exact match first
    cursor.execute("SELECT set_id FROM lego_sets WHERE set_id = ?", (scraped_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Try normalized version
    normalized_id = normalize_set_id(scraped_id)
    cursor.execute("SELECT set_id FROM lego_sets WHERE set_id = ?", (normalized_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Try matching by set number without the variant
    if "-" in scraped_id:
        set_num = scraped_id.split("-")[0]
        cursor.execute("SELECT set_id FROM lego_sets WHERE set_num LIKE ?", (f"{set_num}%",))
        result = cursor.fetchone()
        if result:
            return result[0]
    
    return None

def create_seo_filename(image_url: str, product_id: str, is_high_res: bool = False) -> str:
    """Create an SEO-friendly filename for an image."""
    # Parse the URL
    parsed_url = urlparse(image_url)
    path = parsed_url.path
    
    # Extract a unique identifier from the URL path
    # First, try to get the filename without extension
    filename_part = os.path.basename(path).split('.')[0]
    
    # If the filename is empty or too generic, try to extract a unique ID from the path
    if not filename_part or filename_part == "":
        # Look for patterns like blt1234567890abcdef or alt1, alt2, etc.
        blt_match = re.search(r'(blt[a-f0-9]+)', path)
        alt_match = re.search(r'(alt\d+)', path)
        hero_match = re.search(r'(Hero\d+)', path)
        block_match = re.search(r'(Block_\w+_\d+)', path)
        
        if blt_match:
            unique_id = blt_match.group(1)[:10]  # Take first 10 chars to keep filename reasonable
        elif alt_match:
            unique_id = alt_match.group(1)
        elif hero_match:
            unique_id = hero_match.group(1).lower()
        elif block_match:
            unique_id = block_match.group(1).lower().replace('_', '-')
        else:
            # If no recognizable pattern, use a hash of the path
            import hashlib
            unique_id = hashlib.md5(path.encode()).hexdigest()[:8]
    else:
        unique_id = filename_part
    
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
    elif "alt" in path.lower():
        image_type = f"view-{unique_id}"
    elif "hero" in path.lower():
        image_type = f"hero-{unique_id}"
    elif "block" in path.lower():
        image_type = f"block-{unique_id}"
    
    # Determine file extension
    if path.lower().endswith('.jpg') or path.lower().endswith('.jpeg') or 'format=jpg' in image_url:
        ext = ".jpg"
    else:
        ext = ".png"
    
    # Create the filename
    if is_high_res:
        filename = f"lego-{product_id}-{image_type}-{unique_id}-high-res{ext}"
    else:
        filename = f"lego-{product_id}-{image_type}-{unique_id}{ext}"
    
    # Clean up the filename
    filename = filename.replace("--", "-").replace("--", "-")
    
    # Ensure filename is not too long (max 255 chars for most filesystems)
    if len(filename) > 240:
        # Truncate the filename
        filename = filename[:240] + ext
    
    return filename

def download_image(url: str, local_path: str) -> bool:
    """Download an image from a URL to a local path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
        return False

def optimize_images(product_id: str, cloudflare_domain: Optional[str] = None) -> Dict[str, Any]:
    """Download and optimize images for a product."""
    print(f"Optimizing images for product {product_id}...")
    
    # Create output directory
    output_dir = os.path.join(IMAGES_DIR, product_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the product data
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return {"error": "Product file not found"}
    
    with open(product_path, "r") as f:
        product_data = json.load(f)
    
    # Extract the product info from the nested structure if needed
    if "product" in product_data:
        product_info = product_data["product"]
    else:
        product_info = product_data
    
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
        image_urls.append(product_info["image"])
    
    # Add high-res main image
    if "high_res_image" in product_info:
        high_res_image_urls.append(product_info["high_res_image"])
    
    # Add images array
    if "images" in product_info:
        for img_url in product_info["images"]:
            if img_url not in image_urls:
                image_urls.append(img_url)
    
    # Add high-res images array
    if "high_res_images" in product_info:
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
                if download_image(image_url, local_path):
                    downloaded_count += 1
                    print(f"Downloaded image: {filename}")
                else:
                    print(f"Failed to download image: {filename}")
                    continue
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
            cloudflare_url = None
            if cloudflare_domain:
                cloudflare_url = f"https://{cloudflare_domain}/{product_id}/{filename}"
            
            image_mapping[image_url] = {
                "local_path": local_path,
                "seo_filename": filename,
                "cloudflare_url": cloudflare_url
            }
        except Exception as e:
            print(f"Error processing image {image_url}: {str(e)}")
    
    # Download high-res images
    for high_res_image_url in high_res_image_urls:
        try:
            # Create SEO-friendly filename
            filename = create_seo_filename(high_res_image_url, product_id, is_high_res=True)
            local_path = os.path.join(output_dir, filename)
            
            # Download the image if it doesn't exist
            if not os.path.exists(local_path):
                print(f"Downloading high-res image: {filename}")
                if download_image(high_res_image_url, local_path):
                    high_res_downloaded_count += 1
                    print(f"Downloaded high-res image: {filename}")
                else:
                    print(f"Failed to download high-res image: {filename}")
                    continue
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
            cloudflare_url = None
            if cloudflare_domain:
                cloudflare_url = f"https://{cloudflare_domain}/{product_id}/{filename}"
            
            image_mapping[high_res_image_url] = {
                "local_path": local_path,
                "seo_filename": filename,
                "cloudflare_url": cloudflare_url
            }
        except Exception as e:
            print(f"Error processing high-res image {high_res_image_url}: {str(e)}")
    
    # Save the image mapping
    with open(os.path.join(output_dir, "image_mapping.json"), "w") as f:
        json.dump(image_mapping, f, indent=2)
    
    return {
        "product_id": product_id,
        "images_dir": output_dir,
        "image_mapping": image_mapping,
        "downloaded_count": downloaded_count,
        "high_res_downloaded_count": high_res_downloaded_count,
        "total_images": len(image_mapping)
    }

def get_theme_ancestors(theme_id: str, cursor) -> List[str]:
    """Get all ancestor theme IDs for a given theme."""
    ancestors = []
    current_id = theme_id
    
    while current_id:
        cursor.execute("SELECT parent_id FROM themes WHERE id = ?", (current_id,))
        result = cursor.fetchone()
        if result and result[0]:
            parent_id = result[0]
            ancestors.append(parent_id)
            current_id = parent_id
        else:
            break
    
    return ancestors

def enrich_database_with_product(db_path: str, product_id: str, cloudflare_domain: Optional[str] = None) -> bool:
    """Enrich the database with data from a scraped product."""
    print(f"Enriching database with data for product {product_id}...")
    
    # Load the product data
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return False
    
    with open(product_path, "r") as f:
        product_data = json.load(f)
    
    # Extract the product info from the nested structure if needed
    if "product" in product_data:
        product_info = product_data["product"]
    else:
        product_info = product_data
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find matching catalog ID
    catalog_id = find_matching_catalog_id(product_id, cursor)
    
    if catalog_id:
        print(f"Found matching catalog ID: {catalog_id}")
    else:
        catalog_id = normalize_set_id(product_id)
        print(f"No matching catalog ID found, using normalized ID: {catalog_id}")
    
    try:
        # Update the lego_sets table
        description = product_info.get("description", "")
        specifications = json.dumps(product_info.get("specifications", {}))
        features = json.dumps(product_info.get("features", {}))
        
        # Extract price information
        price = None
        currency = None
        availability = None
        
        if "price" in product_info:
            price_info = product_info["price"]
            if isinstance(price_info, dict):
                price = price_info.get("amount")
                currency = price_info.get("currency")
                availability = price_info.get("availability")
        
        # Update the lego_sets table
        cursor.execute('''
        UPDATE lego_sets SET
            description = ?,
            specifications = ?,
            features = ?,
            price = ?,
            currency = ?,
            availability = ?,
            last_updated = ?
        WHERE set_id = ?
        ''', (
            description,
            specifications,
            features,
            price,
            currency,
            availability,
            datetime.now().isoformat(),
            catalog_id
        ))
        
        # If no rows were updated, the set doesn't exist in the catalog
        if cursor.rowcount == 0:
            print(f"Set {catalog_id} not found in database, inserting as new record")
            
            # Extract theme information
            theme_name = None
            theme_id = None
            
            # Try to extract theme from product info
            if "theme" in product_info:
                theme_name = product_info["theme"]
                
                # Try to find theme ID by name
                cursor.execute("SELECT id FROM themes WHERE name = ?", (theme_name,))
                result = cursor.fetchone()
                if result:
                    theme_id = result[0]
                else:
                    # Create a new theme if it doesn't exist
                    print(f"Theme '{theme_name}' not found in database, creating new theme")
                    cursor.execute("SELECT MAX(id) FROM themes")
                    max_id = cursor.fetchone()[0]
                    theme_id = max_id + 1 if max_id else 1
                    
                    cursor.execute('''
                    INSERT INTO themes (id, name)
                    VALUES (?, ?)
                    ''', (
                        theme_id,
                        theme_name
                    ))
            
            # Insert a new row
            cursor.execute('''
            INSERT INTO lego_sets (
                set_id, set_num, name, description, specifications, features,
                price, currency, availability, theme_id, theme_name, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                catalog_id,
                catalog_id,
                product_info.get("title", ""),
                description,
                specifications,
                features,
                price,
                currency,
                availability,
                theme_id,
                theme_name,
                datetime.now().isoformat()
            ))
            
            # Insert theme relationship if theme_id is available
            if theme_id:
                cursor.execute('''
                INSERT INTO set_themes (set_id, theme_id, is_primary)
                VALUES (?, ?, ?)
                ''', (
                    catalog_id,
                    theme_id,
                    1  # Primary theme
                ))
                
                # Insert ancestor themes
                ancestor_themes = get_theme_ancestors(theme_id, cursor)
                for ancestor_id in ancestor_themes:
                    cursor.execute('''
                    INSERT INTO set_themes (set_id, theme_id, is_primary)
                    VALUES (?, ?, ?)
                    ''', (
                        catalog_id,
                        ancestor_id,
                        0  # Not primary theme
                    ))
        else:
            # Set exists, update theme information if available
            if "theme" in product_info:
                theme_name = product_info["theme"]
                
                # Try to find theme ID by name
                cursor.execute("SELECT id FROM themes WHERE name = ?", (theme_name,))
                result = cursor.fetchone()
                if result:
                    theme_id = result[0]
                    
                    # Update primary theme in lego_sets table
                    cursor.execute('''
                    UPDATE lego_sets SET
                        theme_id = ?,
                        theme_name = ?
                    WHERE set_id = ?
                    ''', (
                        theme_id,
                        theme_name,
                        catalog_id
                    ))
                    
                    # Check if theme relationship already exists
                    cursor.execute('''
                    SELECT id FROM set_themes
                    WHERE set_id = ? AND theme_id = ?
                    ''', (
                        catalog_id,
                        theme_id
                    ))
                    
                    if not cursor.fetchone():
                        # Insert theme relationship
                        cursor.execute('''
                        INSERT INTO set_themes (set_id, theme_id, is_primary)
                        VALUES (?, ?, ?)
                        ''', (
                            catalog_id,
                            theme_id,
                            1  # Primary theme
                        ))
                        
                        # Insert ancestor themes
                        ancestor_themes = get_theme_ancestors(theme_id, cursor)
                        for ancestor_id in ancestor_themes:
                            # Check if ancestor relationship already exists
                            cursor.execute('''
                            SELECT id FROM set_themes
                            WHERE set_id = ? AND theme_id = ?
                            ''', (
                                catalog_id,
                                ancestor_id
                            ))
                            
                            if not cursor.fetchone():
                                cursor.execute('''
                                INSERT INTO set_themes (set_id, theme_id, is_primary)
                                VALUES (?, ?, ?)
                                ''', (
                                    catalog_id,
                                    ancestor_id,
                                    0  # Not primary theme
                                ))
        
        # Import price history
        if "price_history" in product_info:
            for price_entry in product_info["price_history"]:
                try:
                    price_amount = price_entry.get("price")
                    price_currency = price_entry.get("currency")
                    price_source = price_entry.get("source", "lego.com")
                    price_date = price_entry.get("date")
                    
                    if price_amount and price_date:
                        cursor.execute('''
                        INSERT INTO prices (set_id, price, currency, source, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (
                            catalog_id,
                            price_amount,
                            price_currency,
                            price_source,
                            price_date
                        ))
                except Exception as e:
                    print(f"Error importing price history: {str(e)}")
        
        # Import minifigures
        if "minifigures" in product_info:
            for minifig in product_info["minifigures"]:
                try:
                    minifig_name = minifig.get("name", "")
                    minifig_count = minifig.get("count", 1)
                    
                    # Generate a unique fig_id based on the name
                    fig_id = f"{catalog_id}-{minifig_name.lower().replace(' ', '-')}"
                    
                    cursor.execute('''
                    INSERT INTO minifigures (fig_id, set_id, name, count)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        fig_id,
                        catalog_id,
                        minifig_name,
                        minifig_count
                    ))
                except Exception as e:
                    print(f"Error importing minifigure: {str(e)}")
        
        # Optimize images
        image_result = optimize_images(product_id, cloudflare_domain)
        
        if "error" not in image_result:
            image_mapping = image_result["image_mapping"]
            
            # Import images
            # Main image
            if "image" in product_info:
                try:
                    image_url = product_info["image"]
                    cloudflare_url = None
                    
                    if image_url in image_mapping and image_mapping[image_url]["cloudflare_url"]:
                        cloudflare_url = image_mapping[image_url]["cloudflare_url"]
                    
                    cursor.execute('''
                    INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        catalog_id,
                        image_url,
                        cloudflare_url,
                        0,
                        1,
                        "product"
                    ))
                except Exception as e:
                    print(f"Error importing main image: {str(e)}")
            
            # High-res main image
            if "high_res_image" in product_info:
                try:
                    image_url = product_info["high_res_image"]
                    cloudflare_url = None
                    
                    if image_url in image_mapping and image_mapping[image_url]["cloudflare_url"]:
                        cloudflare_url = image_mapping[image_url]["cloudflare_url"]
                    
                    cursor.execute('''
                    INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        catalog_id,
                        image_url,
                        cloudflare_url,
                        1,
                        1,
                        "product"
                    ))
                except Exception as e:
                    print(f"Error importing high-res main image: {str(e)}")
            
            # Additional images
            if "images" in product_info:
                for i, image_url in enumerate(product_info["images"]):
                    try:
                        image_type = "product"
                        if "box" in image_url.lower():
                            image_type = "box"
                        elif "lifestyle" in image_url.lower():
                            image_type = "lifestyle"
                        
                        cloudflare_url = None
                        if image_url in image_mapping and image_mapping[image_url]["cloudflare_url"]:
                            cloudflare_url = image_mapping[image_url]["cloudflare_url"]
                        
                        cursor.execute('''
                        INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            catalog_id,
                            image_url,
                            cloudflare_url,
                            0,
                            0,
                            image_type
                        ))
                    except Exception as e:
                        print(f"Error importing additional image: {str(e)}")
            
            # High-res additional images
            if "high_res_images" in product_info:
                for i, image_url in enumerate(product_info["high_res_images"]):
                    try:
                        image_type = "product"
                        if "box" in image_url.lower():
                            image_type = "box"
                        elif "lifestyle" in image_url.lower():
                            image_type = "lifestyle"
                        
                        cloudflare_url = None
                        if image_url in image_mapping and image_mapping[image_url]["cloudflare_url"]:
                            cloudflare_url = image_mapping[image_url]["cloudflare_url"]
                        
                        cursor.execute('''
                        INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            catalog_id,
                            image_url,
                            cloudflare_url,
                            1,
                            0,
                            image_type
                        ))
                    except Exception as e:
                        print(f"Error importing high-res additional image: {str(e)}")
        
        # Import metadata
        for key, value in product_info.items():
            # Skip keys that are already handled
            if key in ["title", "description", "specifications", "features", "price", "price_history", 
                      "minifigures", "image", "high_res_image", "images", "high_res_images"]:
                continue
            
            # Skip complex objects
            if isinstance(value, (dict, list)):
                continue
            
            try:
                cursor.execute('''
                INSERT INTO metadata (set_id, key, value)
                VALUES (?, ?, ?)
                ''', (
                    catalog_id,
                    key,
                    str(value)
                ))
            except Exception as e:
                print(f"Error importing metadata: {str(e)}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"Successfully enriched database with data for product {product_id}")
        return True
    
    except Exception as e:
        print(f"Error enriching database with product {product_id}: {str(e)}")
        conn.rollback()
        conn.close()
        return False

def enrich_database_with_all_products(db_path: str, cloudflare_domain: Optional[str] = None) -> List[str]:
    """Enrich the database with data from all scraped products."""
    print("Enriching database with data from all scraped products...")
    
    # Get all product files
    product_files = [f for f in os.listdir(PRODUCTS_DIR) if f.startswith("lego_product_") and f.endswith(".json")]
    
    # Extract product IDs
    product_ids = []
    for product_file in product_files:
        match = re.search(r"lego_product_(\d+)\.json", product_file)
        if match:
            product_ids.append(match.group(1))
    
    print(f"Found {len(product_ids)} product files")
    
    # Enrich database with each product
    successful_ids = []
    for product_id in product_ids:
        if enrich_database_with_product(db_path, product_id, cloudflare_domain):
            successful_ids.append(product_id)
    
    print(f"Successfully enriched database with {len(successful_ids)} products")
    return successful_ids

def main():
    parser = argparse.ArgumentParser(description="Enrich the database with scraped product data")
    parser.add_argument("--db", type=str, default=DATABASE_FILE, help="Path to the SQLite database")
    parser.add_argument("--product-id", type=str, help="Enrich database with a specific product ID")
    parser.add_argument("--cloudflare-domain", type=str, help="Cloudflare domain for image URLs")
    
    args = parser.parse_args()
    
    # Ensure all directories exist
    ensure_directories()
    
    # Enrich database
    if args.product_id:
        enrich_database_with_product(args.db, args.product_id, args.cloudflare_domain)
    else:
        enrich_database_with_all_products(args.db, args.cloudflare_domain)

if __name__ == "__main__":
    main() 