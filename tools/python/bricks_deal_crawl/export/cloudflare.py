#!/usr/bin/env python3

import os
import sqlite3
import argparse
import json
from typing import List, Dict, Any, Optional

# Constants
DATABASE_FILE = os.path.join("output", "lego_database.sqlite")
OUTPUT_DIR = os.path.join("d1_export")

def ensure_output_dir():
    """Ensure the output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_drop_tables_script():
    """Create a SQL script to drop existing tables."""
    print("Creating drop tables script...")
    
    drop_path = os.path.join(OUTPUT_DIR, "drop_tables.sql")
    
    with open(drop_path, 'w') as f:
        f.write("-- Drop existing tables\n")
        f.write("DROP TABLE IF EXISTS metadata;\n")
        f.write("DROP TABLE IF EXISTS images;\n")
        f.write("DROP TABLE IF EXISTS prices;\n")
        f.write("DROP TABLE IF EXISTS minifigures;\n")
        f.write("DROP TABLE IF EXISTS set_themes;\n")
        f.write("DROP TABLE IF EXISTS lego_sets;\n")
        f.write("DROP TABLE IF EXISTS themes;\n")
    
    print(f"Drop tables script created at {drop_path}")
    return drop_path

def create_schema_script(db_path: str):
    """Create a SQL script with the database schema."""
    print("Creating schema script...")
    
    schema_path = os.path.join(OUTPUT_DIR, "schema.sql")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, 'w') as f:
        # Get table creation statements for essential tables
        essential_tables = ["themes", "lego_sets", "set_themes", "minifigures", "prices", "images", "metadata"]
        for table_name in essential_tables:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            table = cursor.fetchone()
            if table:
                # Remove any IF NOT EXISTS to ensure clean creation
                table_sql = table[0].replace("IF NOT EXISTS", "")
                f.write(f"{table_sql};\n\n")
        
        # Get index creation statements for essential tables
        for table_name in essential_tables:
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}' AND sql IS NOT NULL;")
            indexes = cursor.fetchall()
            for index in indexes:
                # Remove any IF NOT EXISTS to ensure clean creation
                index_sql = index[0].replace("IF NOT EXISTS", "")
                f.write(f"{index_sql};\n\n")
    
    conn.close()
    
    print(f"Schema script created at {schema_path}")
    return schema_path

def export_table_data(db_path: str, table_name: str, batch_size: int = 100, where_clause: Optional[str] = None):
    """Export data from a table to SQL files in batches."""
    print(f"Exporting data from table {table_name}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get total count
    if where_clause:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}")
    else:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    
    total_count = cursor.fetchone()[0]
    
    if total_count == 0:
        print(f"Table {table_name} is empty. Skipping.")
        conn.close()
        return []
    
    # Calculate number of batches
    num_batches = (total_count + batch_size - 1) // batch_size
    
    # Export data in batches
    data_files = []
    
    for batch_index in range(num_batches):
        offset = batch_index * batch_size
        
        # Get a batch of rows
        if where_clause:
            cursor.execute(f"SELECT * FROM {table_name} WHERE {where_clause} LIMIT {batch_size} OFFSET {offset}")
        else:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
        
        rows = cursor.fetchall()
        
        if not rows:
            continue
        
        # Create a file for this batch
        data_path = os.path.join(OUTPUT_DIR, f"{table_name}_{batch_index}.sql")
        
        with open(data_path, 'w') as f:
            # Write INSERT statements for each row
            for row in rows:
                columns = row.keys()
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
        
        data_files.append(data_path)
        print(f"Exported batch {batch_index + 1}/{num_batches} of table {table_name}")
    
    conn.close()
    
    print(f"Exported {len(data_files)} batches from table {table_name}")
    return data_files

def export_set_data(db_path: str, set_id: str):
    """Export data for a specific set."""
    print(f"Exporting data for set {set_id}...")
    
    # Export lego_sets table
    lego_sets_files = export_table_data(db_path, "lego_sets", where_clause=f"set_id = '{set_id}'")
    
    # Export set_themes table
    set_themes_files = export_table_data(db_path, "set_themes", where_clause=f"set_id = '{set_id}'")
    
    # Get theme IDs for this set
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT theme_id FROM set_themes WHERE set_id = '{set_id}'")
    theme_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Export themes table for related themes
    themes_files = []
    if theme_ids:
        theme_ids_str = ", ".join([f"'{tid}'" for tid in theme_ids])
        themes_files = export_table_data(db_path, "themes", where_clause=f"id IN ({theme_ids_str})")
    
    # Export minifigures table
    minifigures_files = export_table_data(db_path, "minifigures", where_clause=f"set_id = '{set_id}'")
    
    # Export prices table
    prices_files = export_table_data(db_path, "prices", where_clause=f"set_id = '{set_id}'")
    
    # Export images table
    images_files = export_table_data(db_path, "images", where_clause=f"set_id = '{set_id}'")
    
    # Export metadata table
    metadata_files = export_table_data(db_path, "metadata", where_clause=f"set_id = '{set_id}'")
    
    # Combine all files
    all_files = themes_files + lego_sets_files + set_themes_files + minifigures_files + prices_files + images_files + metadata_files
    
    print(f"Exported {len(all_files)} files for set {set_id}")
    return all_files

def export_all_tables(db_path: str, batch_size: int = 100):
    """Export all tables to SQL files."""
    print("Exporting all tables...")
    
    # Export themes table
    themes_files = export_table_data(db_path, "themes", batch_size)
    
    # Export lego_sets table
    lego_sets_files = export_table_data(db_path, "lego_sets", batch_size)
    
    # Export set_themes table
    set_themes_files = export_table_data(db_path, "set_themes", batch_size)
    
    # Export minifigures table
    minifigures_files = export_table_data(db_path, "minifigures", batch_size)
    
    # Export prices table
    prices_files = export_table_data(db_path, "prices", batch_size)
    
    # Export images table
    images_files = export_table_data(db_path, "images", batch_size)
    
    # Export metadata table
    metadata_files = export_table_data(db_path, "metadata", batch_size)
    
    # Combine all files
    all_files = themes_files + lego_sets_files + set_themes_files + minifigures_files + prices_files + images_files + metadata_files
    
    print(f"Exported {len(all_files)} files from all tables")
    return all_files

def create_import_script(drop_path: str, schema_path: str, data_files: List[str], auto_confirm: bool = True):
    """Create a shell script to import the data into Cloudflare D1."""
    print("Creating import script...")
    
    script_path = os.path.join(OUTPUT_DIR, "import_to_d1.sh")
    
    # Add --yes flag if auto_confirm is True
    yes_flag = " --yes" if auto_confirm else ""
    
    with open(script_path, 'w') as f:
        f.write("#!/bin/bash\n\n")
        
        f.write("# Drop existing tables\n")
        f.write(f"wrangler d1 execute bricksdeal --file {drop_path} --remote{yes_flag}\n\n")
        
        f.write("# Import schema\n")
        f.write(f"wrangler d1 execute bricksdeal --file {schema_path} --remote{yes_flag}\n\n")
        
        f.write("# Import data\n")
        for data_file in data_files:
            f.write(f"wrangler d1 execute bricksdeal --file {data_file} --remote{yes_flag}\n")
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    print(f"Import script created at {script_path}")
    return script_path

def main():
    parser = argparse.ArgumentParser(description="Export SQLite database to Cloudflare D1")
    parser.add_argument("--db", type=str, default=DATABASE_FILE, help="Path to the SQLite database")
    parser.add_argument("--set-id", type=str, help="Export data for a specific set ID")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of rows per batch")
    parser.add_argument("--no-auto-confirm", action="store_true", help="Don't add --yes flag to wrangler commands")
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    ensure_output_dir()
    
    # Create drop tables script
    drop_path = create_drop_tables_script()
    
    # Create schema script
    schema_path = create_schema_script(args.db)
    
    # Export data
    if args.set_id:
        data_files = export_set_data(args.db, args.set_id)
    else:
        data_files = export_all_tables(args.db, args.batch_size)
    
    # Create import script
    if data_files:
        script_path = create_import_script(drop_path, schema_path, data_files, not args.no_auto_confirm)
        print("\nExport completed successfully!")
        print("\nNext steps:")
        print(f"1. Run the import script: bash {script_path}")
        print("2. Deploy your Cloudflare Worker: wrangler deploy")
    else:
        print("\nNo data files were exported.")

if __name__ == "__main__":
    main() 