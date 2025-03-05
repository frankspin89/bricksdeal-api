#!/usr/bin/env python3

import os
import sqlite3
import argparse
from typing import List, Dict, Any

# Constants
DATABASE_FILE = os.path.join("output", "lego_database.sqlite")
OUTPUT_DIR = os.path.join("d1_export")

def ensure_output_dir():
    """Ensure the output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def export_schema(db_path: str):
    """Export the database schema to a SQL file."""
    print("Exporting database schema...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the schema file
    schema_path = os.path.join(OUTPUT_DIR, "schema.sql")
    
    with open(schema_path, 'w') as f:
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
    
    print(f"Schema exported to {schema_path}")
    return schema_path

def export_set_data(db_path: str, set_id: str):
    """Export data for a specific set to a SQL file."""
    print(f"Exporting data for set {set_id}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if the set exists
    cursor.execute("SELECT * FROM lego_sets WHERE set_id = ?", (set_id,))
    set_data = cursor.fetchone()
    
    if not set_data:
        print(f"Set {set_id} not found in the database.")
        conn.close()
        return None
    
    # Create the data file
    data_path = os.path.join(OUTPUT_DIR, f"set_{set_id.replace('-', '_')}.sql")
    
    with open(data_path, 'w') as f:
        # Export set data
        columns = set_data.keys()
        values = []
        for value in set_data:
            if value is None:
                values.append("NULL")
            elif isinstance(value, (int, float)):
                values.append(str(value))
            else:
                # Escape single quotes in string values
                values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
        
        f.write(f"-- Set data for {set_id}\n")
        f.write(f"INSERT INTO lego_sets ({', '.join(columns)}) VALUES ({', '.join(values)});\n\n")
        
        # Export minifigures
        cursor.execute("SELECT * FROM minifigures WHERE set_id = ?", (set_id,))
        minifigs = cursor.fetchall()
        
        if minifigs:
            f.write(f"-- Minifigures for {set_id}\n")
            for minifig in minifigs:
                columns = minifig.keys()
                values = []
                for value in minifig:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        # Escape single quotes in string values
                        values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                
                f.write(f"INSERT INTO minifigures ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
            f.write("\n")
        
        # Export prices
        cursor.execute("SELECT * FROM prices WHERE set_id = ?", (set_id,))
        prices = cursor.fetchall()
        
        if prices:
            f.write(f"-- Prices for {set_id}\n")
            for price in prices:
                columns = price.keys()
                values = []
                for value in price:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        # Escape single quotes in string values
                        values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                
                f.write(f"INSERT INTO prices ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
            f.write("\n")
        
        # Export images
        cursor.execute("SELECT * FROM images WHERE set_id = ?", (set_id,))
        images = cursor.fetchall()
        
        if images:
            f.write(f"-- Images for {set_id}\n")
            for image in images:
                columns = image.keys()
                values = []
                for value in image:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        # Escape single quotes in string values
                        values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                
                f.write(f"INSERT INTO images ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
            f.write("\n")
        
        # Export metadata
        cursor.execute("SELECT * FROM metadata WHERE set_id = ?", (set_id,))
        metadata = cursor.fetchall()
        
        if metadata:
            f.write(f"-- Metadata for {set_id}\n")
            for meta in metadata:
                columns = meta.keys()
                values = []
                for value in meta:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        # Escape single quotes in string values
                        values.append(f"'{str(value).replace('\'', '\'\'')}'" if value is not None else "NULL")
                
                f.write(f"INSERT INTO metadata ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
    
    conn.close()
    
    print(f"Data for set {set_id} exported to {data_path}")
    return data_path

def export_all_sets(db_path: str, limit: int = None):
    """Export data for all sets to SQL files."""
    print("Exporting data for all sets...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all set IDs
    if limit:
        cursor.execute("SELECT set_id FROM lego_sets LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT set_id FROM lego_sets")
    
    set_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Export data for each set
    exported_files = []
    for set_id in set_ids:
        data_path = export_set_data(db_path, set_id)
        if data_path:
            exported_files.append(data_path)
    
    print(f"Exported data for {len(exported_files)} sets.")
    return exported_files

def export_drop_tables():
    """Create a SQL file to drop existing tables."""
    print("Creating drop tables script...")
    
    drop_path = os.path.join(OUTPUT_DIR, "drop_tables.sql")
    
    with open(drop_path, 'w') as f:
        f.write("-- Drop existing tables\n")
        f.write("DROP TABLE IF EXISTS metadata;\n")
        f.write("DROP TABLE IF EXISTS images;\n")
        f.write("DROP TABLE IF EXISTS prices;\n")
        f.write("DROP TABLE IF EXISTS minifigures;\n")
        f.write("DROP TABLE IF EXISTS lego_sets;\n")
    
    print(f"Drop tables script created at {drop_path}")
    return drop_path

def generate_import_commands(drop_path: str, schema_path: str, data_files: List[str], auto_confirm: bool = True):
    """Generate wrangler commands to import the data into Cloudflare D1."""
    commands_path = os.path.join(OUTPUT_DIR, "import_commands.sh")
    
    # Add --yes flag if auto_confirm is True
    yes_flag = " --yes" if auto_confirm else ""
    
    with open(commands_path, 'w') as f:
        f.write("#!/bin/bash\n\n")
        
        f.write("# Drop existing tables\n")
        f.write(f"wrangler d1 execute bricksdeal --file {drop_path} --remote{yes_flag}\n\n")
        
        f.write("# Import schema\n")
        f.write(f"wrangler d1 execute bricksdeal --file {schema_path} --remote{yes_flag}\n\n")
        
        f.write("# Import data\n")
        for data_file in data_files:
            f.write(f"wrangler d1 execute bricksdeal --file {data_file} --remote{yes_flag}\n")
    
    # Make the file executable
    os.chmod(commands_path, 0o755)
    
    print(f"Import commands written to {commands_path}")
    return commands_path

def main():
    parser = argparse.ArgumentParser(description="Export SQLite database to Cloudflare D1 SQL files")
    parser.add_argument("--db", type=str, default=DATABASE_FILE, help="Path to the SQLite database")
    parser.add_argument("--set-id", type=str, help="Export data for a specific set ID")
    parser.add_argument("--limit", type=int, help="Limit the number of sets to export")
    parser.add_argument("--no-auto-confirm", action="store_true", help="Don't add --yes flag to wrangler commands")
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    ensure_output_dir()
    
    # Create drop tables script
    drop_path = export_drop_tables()
    
    # Export the schema
    schema_path = export_schema(args.db)
    
    # Export set data
    if args.set_id:
        data_files = [export_set_data(args.db, args.set_id)]
        data_files = [f for f in data_files if f]  # Remove None values
    else:
        data_files = export_all_sets(args.db, args.limit)
    
    # Generate import commands
    if data_files:
        commands_path = generate_import_commands(drop_path, schema_path, data_files, not args.no_auto_confirm)
        print("\nNext steps:")
        print(f"1. Run the import commands: bash {commands_path}")
        print("2. Deploy your Cloudflare Worker: wrangler deploy")
    else:
        print("\nNo data files were exported.")

if __name__ == "__main__":
    main() 