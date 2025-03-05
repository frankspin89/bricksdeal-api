#!/usr/bin/env python3

import os
import json
import argparse
import requests
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import subprocess

# Constants
PRODUCTS_DIR = os.path.join("output", "products")
IMAGES_DIR = os.path.join("output", "images")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_DATABASE_ID = os.environ.get("CLOUDFLARE_DATABASE_ID")

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

def execute_d1_query(query: str, params: List[Any] = None) -> Dict[str, Any]:
    """Execute a query on Cloudflare D1 using the API."""
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_DATABASE_ID:
        raise ValueError("Cloudflare credentials not set. Please set CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and CLOUDFLARE_DATABASE_ID environment variables.")
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "sql": query
    }
    
    if params:
        data["params"] = params
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise Exception(f"Error executing query: {response.text}")
    
    return response.json()

def execute_d1_command(command: str) -> Dict[str, Any]:
    """Execute a D1 command using wrangler CLI."""
    result = subprocess.run(
        ["wrangler", "d1", "execute", "bricksdeal", "--command", command, "--remote", "--yes"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Error executing D1 command: {result.stderr}")
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": True, "result": result.stdout}

def find_set_in_d1(set_id: str) -> Optional[Dict[str, Any]]:
    """Find a set in Cloudflare D1 by ID."""
    try:
        result = execute_d1_command(f"SELECT * FROM lego_sets WHERE set_id = '{set_id}'")
        
        if "results" in result and result["results"] and len(result["results"]) > 0:
            return result["results"][0]
        
        return None
    except Exception as e:
        print(f"Error finding set {set_id} in D1: {str(e)}")
        return None

def find_theme_in_d1(theme_name: str) -> Optional[int]:
    """Find a theme in Cloudflare D1 by name."""
    try:
        result = execute_d1_command(f"SELECT id FROM themes WHERE name = '{theme_name.replace('\'', '\'\'')}'")
        
        if "results" in result and result["results"] and len(result["results"]) > 0:
            return result["results"][0]["id"]
        
        return None
    except Exception as e:
        print(f"Error finding theme {theme_name} in D1: {str(e)}")
        return None

def get_theme_ancestors_in_d1(theme_id: int) -> List[int]:
    """Get all ancestor theme IDs for a given theme in D1."""
    ancestors = []
    current_id = theme_id
    
    while current_id:
        try:
            result = execute_d1_command(f"SELECT parent_id FROM themes WHERE id = {current_id}")
            
            if "results" in result and result["results"] and len(result["results"]) > 0 and result["results"][0]["parent_id"]:
                parent_id = result["results"][0]["parent_id"]
                ancestors.append(parent_id)
                current_id = parent_id
            else:
                break
        except Exception as e:
            print(f"Error getting theme ancestors for {theme_id} in D1: {str(e)}")
            break
    
    return ancestors

def create_theme_in_d1(theme_name: str) -> Optional[int]:
    """Create a new theme in Cloudflare D1."""
    try:
        # Get the next available ID
        result = execute_d1_command("SELECT MAX(id) as max_id FROM themes")
        
        if "results" in result and result["results"] and len(result["results"]) > 0:
            max_id = result["results"][0]["max_id"]
            new_id = max_id + 1 if max_id else 1
        else:
            new_id = 1
        
        # Create the theme
        execute_d1_command(f"INSERT INTO themes (id, name) VALUES ({new_id}, '{theme_name.replace('\'', '\'\'')}')")
        
        return new_id
    except Exception as e:
        print(f"Error creating theme {theme_name} in D1: {str(e)}")
        return None

def update_set_in_d1(set_id: str, product_info: Dict[str, Any]) -> bool:
    """Update a set in Cloudflare D1 with data from a JSON file."""
    try:
        # Check if the set exists
        existing_set = find_set_in_d1(set_id)
        
        # Extract basic information
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
        
        # Extract theme information
        theme_name = product_info.get("theme")
        theme_id = None
        
        if theme_name:
            # Find or create the theme
            theme_id = find_theme_in_d1(theme_name)
            
            if not theme_id:
                theme_id = create_theme_in_d1(theme_name)
        
        if existing_set:
            # Update the existing set
            update_query = f"""
            UPDATE lego_sets SET
                description = '{description.replace("'", "''")}',
                specifications = '{specifications.replace("'", "''")}',
                features = '{features.replace("'", "''")}',
                price = {price if price is not None else 'NULL'},
                currency = '{currency.replace("'", "''")}' if currency else 'NULL',
                availability = '{availability.replace("'", "''")}' if availability else 'NULL',
                last_updated = '{datetime.now().isoformat()}'
            """
            
            if theme_id and theme_name:
                update_query += f"""
                , theme_id = {theme_id},
                theme_name = '{theme_name.replace("'", "''")}'
                """
            
            update_query += f" WHERE set_id = '{set_id}'"
            
            execute_d1_command(update_query)
            
            # Update theme relationships if theme_id is available
            if theme_id:
                # Check if the primary theme relationship exists
                result = execute_d1_command(f"SELECT id FROM set_themes WHERE set_id = '{set_id}' AND theme_id = {theme_id}")
                
                if not "results" in result or not result["results"] or len(result["results"]) == 0:
                    # Insert primary theme relationship
                    execute_d1_command(f"INSERT INTO set_themes (set_id, theme_id, is_primary) VALUES ('{set_id}', {theme_id}, 1)")
                
                # Get ancestor themes
                ancestor_themes = get_theme_ancestors_in_d1(theme_id)
                
                for ancestor_id in ancestor_themes:
                    # Check if the ancestor relationship exists
                    result = execute_d1_command(f"SELECT id FROM set_themes WHERE set_id = '{set_id}' AND theme_id = {ancestor_id}")
                    
                    if not "results" in result or not result["results"] or len(result["results"]) == 0:
                        # Insert ancestor theme relationship
                        execute_d1_command(f"INSERT INTO set_themes (set_id, theme_id, is_primary) VALUES ('{set_id}', {ancestor_id}, 0)")
        else:
            # Insert a new set
            title = product_info.get("title", "").replace("'", "''")
            
            insert_query = f"""
            INSERT INTO lego_sets (
                set_id, set_num, name, description, specifications, features,
                price, currency, availability, theme_id, theme_name, last_updated
            ) VALUES (
                '{set_id}',
                '{set_id}',
                '{title}',
                '{description.replace("'", "''")}',
                '{specifications.replace("'", "''")}',
                '{features.replace("'", "''")}',
                {price if price is not None else 'NULL'},
                '{currency.replace("'", "''")}' if currency else NULL,
                '{availability.replace("'", "''")}' if availability else NULL,
                {theme_id if theme_id is not None else 'NULL'},
                '{theme_name.replace("'", "''")}' if theme_name else NULL,
                '{datetime.now().isoformat()}'
            )
            """
            
            execute_d1_command(insert_query)
            
            # Insert theme relationships if theme_id is available
            if theme_id:
                # Insert primary theme relationship
                execute_d1_command(f"INSERT INTO set_themes (set_id, theme_id, is_primary) VALUES ('{set_id}', {theme_id}, 1)")
                
                # Get ancestor themes
                ancestor_themes = get_theme_ancestors_in_d1(theme_id)
                
                for ancestor_id in ancestor_themes:
                    # Insert ancestor theme relationship
                    execute_d1_command(f"INSERT INTO set_themes (set_id, theme_id, is_primary) VALUES ('{set_id}', {ancestor_id}, 0)")
        
        # Update price history
        if "price_history" in product_info:
            for price_entry in product_info["price_history"]:
                price_amount = price_entry.get("price")
                price_currency = price_entry.get("currency", "").replace("'", "''")
                price_source = price_entry.get("source", "lego.com").replace("'", "''")
                price_date = price_entry.get("date")
                
                if price_amount and price_date:
                    # Check if this price entry already exists
                    result = execute_d1_command(f"""
                    SELECT id FROM prices 
                    WHERE set_id = '{set_id}' 
                    AND price = {price_amount} 
                    AND currency = '{price_currency}' 
                    AND source = '{price_source}' 
                    AND timestamp = '{price_date}'
                    """)
                    
                    if not "results" in result or not result["results"] or len(result["results"]) == 0:
                        # Insert new price entry
                        execute_d1_command(f"""
                        INSERT INTO prices (set_id, price, currency, source, timestamp)
                        VALUES ('{set_id}', {price_amount}, '{price_currency}', '{price_source}', '{price_date}')
                        """)
        
        # Update minifigures
        if "minifigures" in product_info:
            for minifig in product_info["minifigures"]:
                minifig_name = minifig.get("name", "").replace("'", "''")
                minifig_count = minifig.get("count", 1)
                
                # Generate a unique fig_id based on the name
                fig_id = f"{set_id}-{minifig_name.lower().replace(' ', '-').replace('\'', '')}"
                
                # Check if this minifigure already exists
                result = execute_d1_command(f"SELECT id FROM minifigures WHERE fig_id = '{fig_id}'")
                
                if not "results" in result or not result["results"] or len(result["results"]) == 0:
                    # Insert new minifigure
                    execute_d1_command(f"""
                    INSERT INTO minifigures (fig_id, set_id, name, count)
                    VALUES ('{fig_id}', '{set_id}', '{minifig_name}', {minifig_count})
                    """)
        
        # Update images
        # This would typically involve uploading images to Cloudflare R2 and then updating the database
        # For simplicity, we'll just update the database with the image URLs
        
        # Main image
        if "image" in product_info:
            image_url = product_info["image"].replace("'", "''")
            cloudflare_url = None
            
            # Check if this image already exists
            result = execute_d1_command(f"""
            SELECT id FROM images 
            WHERE set_id = '{set_id}' 
            AND url = '{image_url}' 
            AND is_main_image = 1 
            AND is_high_res = 0
            """)
            
            if not "results" in result or not result["results"] or len(result["results"]) == 0:
                # Insert new image
                execute_d1_command(f"""
                INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                VALUES ('{set_id}', '{image_url}', NULL, 0, 1, 'product')
                """)
        
        # High-res main image
        if "high_res_image" in product_info:
            image_url = product_info["high_res_image"].replace("'", "''")
            cloudflare_url = None
            
            # Check if this image already exists
            result = execute_d1_command(f"""
            SELECT id FROM images 
            WHERE set_id = '{set_id}' 
            AND url = '{image_url}' 
            AND is_main_image = 1 
            AND is_high_res = 1
            """)
            
            if not "results" in result or not result["results"] or len(result["results"]) == 0:
                # Insert new image
                execute_d1_command(f"""
                INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                VALUES ('{set_id}', '{image_url}', NULL, 1, 1, 'product')
                """)
        
        # Additional images
        if "images" in product_info:
            for image_url in product_info["images"]:
                image_url = image_url.replace("'", "''")
                image_type = "product"
                
                if "box" in image_url.lower():
                    image_type = "box"
                elif "lifestyle" in image_url.lower():
                    image_type = "lifestyle"
                
                # Check if this image already exists
                result = execute_d1_command(f"""
                SELECT id FROM images 
                WHERE set_id = '{set_id}' 
                AND url = '{image_url}' 
                AND is_main_image = 0 
                AND is_high_res = 0
                """)
                
                if not "results" in result or not result["results"] or len(result["results"]) == 0:
                    # Insert new image
                    execute_d1_command(f"""
                    INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                    VALUES ('{set_id}', '{image_url}', NULL, 0, 0, '{image_type}')
                    """)
        
        # High-res additional images
        if "high_res_images" in product_info:
            for image_url in product_info["high_res_images"]:
                image_url = image_url.replace("'", "''")
                image_type = "product"
                
                if "box" in image_url.lower():
                    image_type = "box"
                elif "lifestyle" in image_url.lower():
                    image_type = "lifestyle"
                
                # Check if this image already exists
                result = execute_d1_command(f"""
                SELECT id FROM images 
                WHERE set_id = '{set_id}' 
                AND url = '{image_url}' 
                AND is_main_image = 0 
                AND is_high_res = 1
                """)
                
                if not "results" in result or not result["results"] or len(result["results"]) == 0:
                    # Insert new image
                    execute_d1_command(f"""
                    INSERT INTO images (set_id, url, cloudflare_url, is_high_res, is_main_image, type)
                    VALUES ('{set_id}', '{image_url}', NULL, 1, 0, '{image_type}')
                    """)
        
        # Update metadata
        for key, value in product_info.items():
            # Skip keys that are already handled
            if key in ["title", "description", "specifications", "features", "price", "price_history", 
                      "minifigures", "image", "high_res_image", "images", "high_res_images", "theme"]:
                continue
            
            # Skip complex objects
            if isinstance(value, (dict, list)):
                continue
            
            # Convert value to string
            str_value = str(value).replace("'", "''")
            
            # Check if this metadata already exists
            result = execute_d1_command(f"""
            SELECT id FROM metadata 
            WHERE set_id = '{set_id}' 
            AND key = '{key.replace("'", "''")}'
            """)
            
            if "results" in result and result["results"] and len(result["results"]) > 0:
                # Update existing metadata
                execute_d1_command(f"""
                UPDATE metadata 
                SET value = '{str_value}' 
                WHERE set_id = '{set_id}' 
                AND key = '{key.replace("'", "''")}'
                """)
            else:
                # Insert new metadata
                execute_d1_command(f"""
                INSERT INTO metadata (set_id, key, value)
                VALUES ('{set_id}', '{key.replace("'", "''")}', '{str_value}')
                """)
        
        return True
    except Exception as e:
        print(f"Error updating set {set_id} in D1: {str(e)}")
        return False

def update_d1_with_product(product_id: str) -> bool:
    """Update Cloudflare D1 with data from a product JSON file."""
    print(f"Updating D1 with data for product {product_id}...")
    
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
    
    # Normalize the set ID
    set_id = normalize_set_id(product_id)
    
    # Update the set in D1
    success = update_set_in_d1(set_id, product_info)
    
    if success:
        print(f"Successfully updated D1 with data for product {product_id}")
    else:
        print(f"Failed to update D1 with data for product {product_id}")
    
    return success

def update_d1_with_all_products() -> List[str]:
    """Update Cloudflare D1 with data from all product JSON files."""
    print("Updating D1 with data from all product files...")
    
    # Get all product files
    product_files = [f for f in os.listdir(PRODUCTS_DIR) if f.startswith("lego_product_") and f.endswith(".json")]
    
    # Extract product IDs
    product_ids = []
    for product_file in product_files:
        match = re.search(r"lego_product_(\d+)\.json", product_file)
        if match:
            product_ids.append(match.group(1))
    
    print(f"Found {len(product_ids)} product files")
    
    # Update D1 with each product
    successful_ids = []
    for product_id in product_ids:
        if update_d1_with_product(product_id):
            successful_ids.append(product_id)
    
    print(f"Successfully updated D1 with {len(successful_ids)} products")
    return successful_ids

def main():
    parser = argparse.ArgumentParser(description="Update Cloudflare D1 directly with data from JSON files")
    parser.add_argument("--product-id", type=str, help="Update D1 with a specific product ID")
    
    args = parser.parse_args()
    
    # Ensure all directories exist
    ensure_directories()
    
    # Update D1
    if args.product_id:
        update_d1_with_product(args.product_id)
    else:
        update_d1_with_all_products()

if __name__ == "__main__":
    main() 