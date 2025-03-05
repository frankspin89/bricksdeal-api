#!/usr/bin/env python3
import os
import json
import sqlite3
import csv
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
LEGO_CATALOG_FILE = os.path.join("input", "lego-catalog.csv")
LEGO_THEMES_FILE = os.path.join("input", "themes.csv")
PRODUCTS_DIR = os.path.join("output", "products")
DATABASE_FILE = os.path.join("output", "lego_database.sqlite")

def create_database(db_path: str) -> None:
    """Create the SQLite database with all necessary tables."""
    print(f"Creating database at {db_path}...")
    
    # Connect to the database (will create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create lego_sets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lego_sets (
        id TEXT PRIMARY KEY,
        name TEXT,
        theme TEXT,
        year_released INTEGER,
        piece_count INTEGER,
        age_range TEXT,
        min_age INTEGER,
        dimensions TEXT,
        weight TEXT,
        instructions_url TEXT,
        is_retired BOOLEAN DEFAULT 0,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create minifigures table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS minifigures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT,
        name TEXT,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (set_id) REFERENCES lego_sets(id)
    )
    ''')
    
    # Create prices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT,
        price REAL,
        currency TEXT,
        date TIMESTAMP,
        source TEXT,
        FOREIGN KEY (set_id) REFERENCES lego_sets(id)
    )
    ''')
    
    # Create images table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT,
        url TEXT,
        cloudflare_url TEXT,
        is_high_res BOOLEAN DEFAULT 0,
        is_main_image BOOLEAN DEFAULT 0,
        type TEXT,
        FOREIGN KEY (set_id) REFERENCES lego_sets(id)
    )
    ''')
    
    # Create metadata table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT,
        key TEXT,
        value TEXT,
        FOREIGN KEY (set_id) REFERENCES lego_sets(id)
    )
    ''')
    
    # Create index for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_set_id_prices ON prices(set_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_set_id_images ON images(set_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_set_id_metadata ON metadata(set_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_set_id_minifigures ON minifigures(set_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database created successfully!")

def import_lego_catalog(db_path: str, catalog_path: str) -> None:
    """Import the LEGO catalog CSV into the database."""
    if not os.path.exists(catalog_path):
        print(f"Error: LEGO catalog file not found at {catalog_path}")
        return
    
    print(f"Importing LEGO catalog from {catalog_path}...")
    
    # Load themes mapping
    themes_map = {}
    themes_file = LEGO_THEMES_FILE
    if os.path.exists(themes_file):
        print("Loading themes mapping...")
        with open(themes_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                themes_map[row.get('id')] = row.get('name')
        print(f"Loaded {len(themes_map)} themes")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read the CSV file
    with open(catalog_path, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        
        # Get the total number of rows for progress reporting
        total_rows = sum(1 for _ in open(catalog_path, 'r', encoding='utf-8')) - 1  # Subtract header row
        
        # Reset file pointer
        f.seek(0)
        next(csv_reader)  # Skip header row
        
        # Process each row
        count = 0
        for row in csv_reader:
            set_id = row.get('set_num', '').strip()
            
            if not set_id:
                continue
                
            # Extract year from the set_num if available (format: number-1)
            year_released = row.get('year')
            if not year_released and '-' in set_id:
                try:
                    year_released = int(set_id.split('-')[1])
                except (ValueError, IndexError):
                    pass
            
            # Try to parse piece count
            piece_count = None
            if row.get('num_parts'):
                try:
                    piece_count = int(row.get('num_parts'))
                except ValueError:
                    pass
            
            # Get theme name from theme_id
            theme_name = row.get('theme_name', '')
            theme_id = row.get('theme_id', '')
            if not theme_name and theme_id and theme_id in themes_map:
                theme_name = themes_map[theme_id]
            
            # Insert into lego_sets table
            cursor.execute('''
            INSERT OR REPLACE INTO lego_sets (
                id, name, theme, year_released, piece_count
            ) VALUES (?, ?, ?, ?, ?)
            ''', (
                set_id,
                row.get('name', ''),
                theme_name,
                year_released,
                piece_count
            ))
            
            count += 1
            if count % 1000 == 0:
                print(f"Processed {count}/{total_rows} sets...")
                conn.commit()
    
    # Commit final changes
    conn.commit()
    conn.close()
    
    print(f"Successfully imported {count} LEGO sets!")

def import_scraped_data(db_path: str, products_dir: str) -> None:
    """Import scraped product data into the database."""
    if not os.path.exists(products_dir):
        print(f"Error: Products directory not found at {products_dir}")
        return
    
    print(f"Importing scraped product data from {products_dir}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all product files
    product_files = [f for f in os.listdir(products_dir) if f.startswith("lego_product_") and f.endswith(".json")]
    
    print(f"Found {len(product_files)} product files to import.")
    
    # Process each product file
    for filename in product_files:
        product_id = filename.replace("lego_product_", "").replace(".json", "")
        file_path = os.path.join(products_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            
            # Check if the product data has a nested structure
            if "product" in product_data:
                product_info = product_data["product"]
                metadata = product_data.get("metadata", {})
            else:
                product_info = product_data
                metadata = product_data.get("metadata", {})
            
            # Update lego_sets table with additional information
            update_fields = []
            update_values = []
            
            if "title" in product_info:
                update_fields.append("name = ?")
                update_values.append(product_info["title"])
            
            if "piece_count" in product_info:
                update_fields.append("piece_count = ?")
                update_values.append(product_info["piece_count"])
            
            if "age_range" in product_info:
                update_fields.append("age_range = ?")
                update_values.append(product_info["age_range"])
            
            if "min_age" in product_info:
                update_fields.append("min_age = ?")
                update_values.append(product_info["min_age"])
            
            if "dimensions" in product_info:
                update_fields.append("dimensions = ?")
                update_values.append(product_info["dimensions"])
            
            if "theme" in product_info:
                update_fields.append("theme = ?")
                update_values.append(product_info["theme"])
            
            if "instructions_url" in product_info:
                update_fields.append("instructions_url = ?")
                update_values.append(product_info["instructions_url"])
            
            if update_fields:
                update_fields.append("date_updated = CURRENT_TIMESTAMP")
                update_query = f"UPDATE lego_sets SET {', '.join(update_fields)} WHERE id = ?"
                update_values.append(product_id)
                cursor.execute(update_query, update_values)
            
            # Insert minifigures
            print(f"Checking minifigures for set {product_id}")
            
            # Check if specs field exists and contains minifigure information
            if "specs" in product_info:
                specs = product_info["specs"]
                print(f"Found specs: {specs}")
                
                if isinstance(specs, dict):
                    if "minifigures" in specs:
                        print(f"Found minifigures count in specs: {specs['minifigures']}")
                    
                    if "minifigure_names" in specs:
                        print(f"Found minifigure_names in specs: {specs['minifigure_names']}")
                    
                    if "minifigures" in specs and "minifigure_names" in specs:
                        # Delete existing minifigures for this set
                        cursor.execute("DELETE FROM minifigures WHERE set_id = ?", (product_id,))
                        
                        # Get minifigure count
                        minifigure_count = specs["minifigures"]
                        
                        # Insert new minifigures
                        minifigure_names_str = specs["minifigure_names"]
                        
                        # Handle different formats of minifigure names
                        if "," in minifigure_names_str:
                            # Split by comma
                            minifigure_names = [name.strip() for name in minifigure_names_str.split(",")]
                        elif " and " in minifigure_names_str:
                            # Split by "and"
                            parts = minifigure_names_str.split(" and ")
                            if len(parts) > 1:
                                last_name = parts[-1].strip()
                                other_names = [name.strip() for name in " ".join(parts[:-1]).split() if name.strip()]
                                minifigure_names = other_names + [last_name]
                            else:
                                minifigure_names = [parts[0].strip()]
                        else:
                            # Just split by space, but be smarter about it
                            # Look for capital letters as potential name starts
                            names = []
                            current_name = ""
                            
                            for word in minifigure_names_str.split():
                                if word.strip() in ["and", "the", "with", "plus"]:
                                    if current_name:
                                        names.append(current_name.strip())
                                        current_name = ""
                                    continue
                                    
                                if word and word[0].isupper() and current_name:
                                    names.append(current_name.strip())
                                    current_name = word
                                else:
                                    if current_name:
                                        current_name += " " + word
                                    else:
                                        current_name = word
                            
                            if current_name:
                                names.append(current_name.strip())
                            
                            minifigure_names = names
                        
                        # If we couldn't parse names properly, just use the original string
                        if not minifigure_names:
                            minifigure_names = [minifigure_names_str]
                        
                        print(f"Importing {len(minifigure_names)} minifigures for set {product_id}: {minifigure_names}")
                        
                        for name in minifigure_names:
                            if name.strip():
                                cursor.execute('''
                                INSERT INTO minifigures (set_id, name)
                                VALUES (?, ?)
                                ''', (product_id, name.strip()))
            
            # Insert price history
            if "price_history" in metadata:
                # Delete existing prices for this set
                cursor.execute("DELETE FROM prices WHERE set_id = ?", (product_id,))
                
                # Insert price history
                for price_entry in metadata["price_history"]:
                    cursor.execute('''
                    INSERT INTO prices (set_id, price, currency, date, source)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        product_id,
                        price_entry["price"],
                        price_entry["currency"],
                        price_entry["date"],
                        "lego.com"
                    ))
            
            # Insert images
            if "image" in product_info or "images" in product_info:
                # Delete existing images for this set
                cursor.execute("DELETE FROM images WHERE set_id = ?", (product_id,))
                
                # Insert main image
                if "image" in product_info:
                    cursor.execute('''
                    INSERT INTO images (set_id, url, is_main_image, type)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        product_id,
                        product_info["image"],
                        1,
                        "product"
                    ))
                
                # Insert high-res main image
                if "high_res_image" in product_info:
                    cursor.execute('''
                    INSERT INTO images (set_id, url, is_high_res, is_main_image, type)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        product_id,
                        product_info["high_res_image"],
                        1,
                        1,
                        "product"
                    ))
                
                # Insert additional images
                if "images" in product_info:
                    for i, image_url in enumerate(product_info["images"]):
                        image_type = "product"
                        if "box" in image_url.lower():
                            image_type = "box"
                        elif "detail" in image_url.lower():
                            image_type = "detail"
                        
                        cursor.execute('''
                        INSERT INTO images (set_id, url, is_main_image, type)
                        VALUES (?, ?, ?, ?)
                        ''', (
                            product_id,
                            image_url,
                            0,
                            image_type
                        ))
                
                # Insert high-res additional images
                if "high_res_images" in product_info:
                    for i, image_url in enumerate(product_info["high_res_images"]):
                        image_type = "product"
                        if "box" in image_url.lower():
                            image_type = "box"
                        elif "detail" in image_url.lower():
                            image_type = "detail"
                        
                        cursor.execute('''
                        INSERT INTO images (set_id, url, is_high_res, is_main_image, type)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (
                            product_id,
                            image_url,
                            1,
                            0,
                            image_type
                        ))
            
            # Insert additional metadata
            for key, value in metadata.items():
                if key != "price_history" and not isinstance(value, (list, dict)):
                    cursor.execute('''
                    INSERT OR REPLACE INTO metadata (set_id, key, value)
                    VALUES (?, ?, ?)
                    ''', (
                        product_id,
                        key,
                        str(value)
                    ))
            
            print(f"Imported data for set {product_id}")
            
        except Exception as e:
            print(f"Error importing data for set {product_id}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("Scraped data import completed!")

def export_to_cloudflare_d1(db_path: str) -> None:
    """Export the SQLite database to Cloudflare D1."""
    print("Preparing to export database to Cloudflare D1...")
    
    # Check if wrangler is installed
    wrangler_installed = False
    try:
        result = os.system("which wrangler > /dev/null 2>&1")
        wrangler_installed = result == 0
    except Exception:
        wrangler_installed = False
    
    if not wrangler_installed:
        print("\nError: Wrangler CLI not found.")
        print("\nTo install Wrangler CLI, follow these steps:")
        print("1. Make sure you have Node.js installed (https://nodejs.org/)")
        print("2. Run: npm install -g wrangler")
        print("3. Run: wrangler login")
        print("\nAfter installing Wrangler, run this command again to export the database to Cloudflare D1.")
        return
    
    # Export the database
    try:
        # Get the database ID from wrangler.toml
        database_id = None
        if os.path.exists("wrangler.toml"):
            with open("wrangler.toml", "r") as f:
                for line in f:
                    if "database_id" in line:
                        database_id = line.split("=")[1].strip().strip('"').strip("'")
                        break
        
        if not database_id:
            print("\nError: Could not find database_id in wrangler.toml")
            print("Please update wrangler.toml with the database_id")
            return
        
        # Create a temporary directory for the SQL dump
        os.makedirs("tmp", exist_ok=True)
        
        # First, create a drop tables script
        drop_tables_path = os.path.join("tmp", "drop_tables.sql")
        with open(drop_tables_path, 'w') as f:
            # Drop only the essential tables
            f.write("DROP TABLE IF EXISTS metadata;\n")
            f.write("DROP TABLE IF EXISTS images;\n")
            f.write("DROP TABLE IF EXISTS prices;\n")
            f.write("DROP TABLE IF EXISTS minifigures;\n")
            f.write("DROP TABLE IF EXISTS lego_sets;\n")
        
        # Execute the drop tables script
        print("Dropping existing tables...")
        drop_cmd = f"echo 'y' | wrangler d1 execute bricksdeal --file {drop_tables_path} --remote --yes"
        drop_result = os.system(drop_cmd)
        
        if drop_result != 0:
            print("\nWarning: Error dropping tables. Continuing anyway...")
        
        # Create a schema file with only the essential tables
        schema_path = os.path.join("tmp", "schema.sql")
        
        # Extract schema (tables, indexes, etc.) without data
        print("Extracting database schema...")
        with open(schema_path, 'w') as f:
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table creation statements for essential tables only
            essential_tables = ["lego_sets", "minifigures", "prices", "images", "metadata"]
            for table_name in essential_tables:
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                table = cursor.fetchone()
                if table:
                    # Remove any IF NOT EXISTS to ensure clean creation
                    table_sql = table[0].replace("IF NOT EXISTS", "")
                    f.write(f"{table_sql};\n\n")
            
            # Get index creation statements for essential tables only
            for table_name in essential_tables:
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}' AND sql IS NOT NULL;")
                indexes = cursor.fetchall()
                for index in indexes:
                    # Remove any IF NOT EXISTS to ensure clean creation
                    index_sql = index[0].replace("IF NOT EXISTS", "")
                    f.write(f"{index_sql};\n\n")
            
            conn.close()
        
        # Now create separate data files for each table in the correct order
        # The order should be: parent tables first, then child tables
        
        # Define the order of tables for import
        table_order = ["lego_sets", "minifigures", "prices", "images", "metadata"]
        
        # Create a data file for each table
        data_files = []
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Define a smaller batch size for Cloudflare D1
        batch_size = 50
        max_rows_per_file = 500
        
        for table_name in table_order:
            print(f"Extracting data from table {table_name}...")
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [column['name'] for column in cursor.fetchall()]
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            
            # Skip empty tables
            if row_count == 0:
                print(f"Table {table_name} is empty. Skipping.")
                continue
            
            # For large tables, split into multiple files
            if row_count > max_rows_per_file:
                print(f"Table {table_name} has {row_count} rows. Splitting into multiple files.")
                
                # Calculate number of files needed
                num_files = (row_count + max_rows_per_file - 1) // max_rows_per_file
                
                for file_index in range(num_files):
                    offset = file_index * max_rows_per_file
                    limit = max_rows_per_file
                    
                    # Get a batch of rows
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset};")
                    rows = cursor.fetchall()
                    
                    # Create a file for this batch
                    data_path = os.path.join("tmp", f"{table_name}_{file_index}.sql")
                    
                    with open(data_path, 'w') as f:
                        # Write INSERT statements for each row
                        for row in rows:
                            values = []
                            for value in row:
                                if value is None:
                                    values.append("NULL")
                                elif isinstance(value, (int, float)):
                                    values.append(str(value))
                                else:
                                    # Escape single quotes in string values
                                    values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                            
                            f.write(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                    
                    data_files.append((table_name, data_path))
            else:
                # For small tables, create a single file
                cursor.execute(f"SELECT * FROM {table_name};")
                rows = cursor.fetchall()
                
                data_path = os.path.join("tmp", f"{table_name}.sql")
                
                with open(data_path, 'w') as f:
                    # Write INSERT statements for each row
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append("NULL")
                            elif isinstance(value, (int, float)):
                                values.append(str(value))
                            else:
                                # Escape single quotes in string values
                                values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                        
                        f.write(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                
                data_files.append((table_name, data_path))
        
        conn.close()
        
        # Now execute the schema and data SQL files on Cloudflare D1
        print("Creating tables in Cloudflare D1...")
        schema_cmd = f"echo 'y' | wrangler d1 execute bricksdeal --file {schema_path} --remote --yes"
        schema_result = os.system(schema_cmd)
        
        if schema_result != 0:
            print("\nError creating tables in Cloudflare D1.")
            print("Please check the error message above and try again.")
            return
        
        # Import data for each table in order
        for table_name, data_path in data_files:
            print(f"Importing data for table {table_name} from {data_path}...")
            data_cmd = f"echo 'y' | wrangler d1 execute bricksdeal --file {data_path} --remote --yes"
            data_result = os.system(data_cmd)
            
            if data_result != 0:
                print(f"\nError importing data for table {table_name} from {data_path}.")
                print("Please check the error message above.")
                print("Continuing with next table...")
        
        print("\nDatabase export completed!")
        print("\nNext steps:")
        print("1. Deploy your Cloudflare Worker with: wrangler deploy")
        print("2. Access your API at: https://lego-database-worker.<your-subdomain>.workers.dev/")
        
        # Clean up temporary files
        os.remove(schema_path)
        os.remove(drop_tables_path)
        for _, data_path in data_files:
            if os.path.exists(data_path):
                os.remove(data_path)
        
    except Exception as e:
        print(f"Error exporting to Cloudflare D1: {e}")

def main():
    parser = argparse.ArgumentParser(description="Set up and populate the LEGO database")
    parser.add_argument("--create", action="store_true", help="Create the database schema")
    parser.add_argument("--import-catalog", action="store_true", help="Import the LEGO catalog")
    parser.add_argument("--import-scraped", action="store_true", help="Import scraped product data")
    parser.add_argument("--export-to-d1", action="store_true", help="Export the database to Cloudflare D1")
    parser.add_argument("--all", action="store_true", help="Perform all operations")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # Perform operations based on arguments
    if args.create or args.all:
        create_database(DATABASE_FILE)
    
    if args.import_catalog or args.all:
        import_lego_catalog(DATABASE_FILE, LEGO_CATALOG_FILE)
    
    if args.import_scraped or args.all:
        import_scraped_data(DATABASE_FILE, PRODUCTS_DIR)
    
    if args.export_to_d1 or args.all:
        export_to_cloudflare_d1(DATABASE_FILE)

if __name__ == "__main__":
    main() 