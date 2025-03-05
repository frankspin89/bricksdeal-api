#!/usr/bin/env python3

import os
import sqlite3
import csv
import gzip
import argparse
from typing import Dict, List, Any

# Constants
LEGO_CATALOG_DIR = os.path.join("input", "lego-catalog")
OUTPUT_DIR = os.path.join("output")
DATABASE_FILE = os.path.join(OUTPUT_DIR, "lego_database.sqlite")

def ensure_output_dir():
    """Ensure the output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_database(db_path: str):
    """Create a new SQLite database with essential tables."""
    print(f"Creating database at {db_path}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    
    # Themes table
    cursor.execute('''
    CREATE TABLE themes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        parent_id INTEGER,
        FOREIGN KEY (parent_id) REFERENCES themes(id)
    )
    ''')
    
    # LEGO Sets table
    cursor.execute('''
    CREATE TABLE lego_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL UNIQUE,
        set_num TEXT NOT NULL,
        name TEXT NOT NULL,
        year INTEGER,
        theme_id INTEGER,  -- Primary theme ID
        theme_name TEXT,   -- Primary theme name
        num_parts INTEGER,
        img_url TEXT,
        description TEXT,
        specifications TEXT,
        features TEXT,
        price REAL,
        currency TEXT,
        availability TEXT,
        last_updated TIMESTAMP,
        FOREIGN KEY (theme_id) REFERENCES themes(id)
    )
    ''')
    
    # Set-Themes junction table for many-to-many relationships
    cursor.execute('''
    CREATE TABLE set_themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        theme_id INTEGER NOT NULL,
        is_primary BOOLEAN DEFAULT 0,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id),
        FOREIGN KEY (theme_id) REFERENCES themes(id),
        UNIQUE(set_id, theme_id)
    )
    ''')
    
    # Minifigures table
    cursor.execute('''
    CREATE TABLE minifigures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fig_id TEXT NOT NULL,
        set_id TEXT NOT NULL,
        name TEXT NOT NULL,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    )
    ''')
    
    # Prices table
    cursor.execute('''
    CREATE TABLE prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        price REAL NOT NULL,
        currency TEXT NOT NULL,
        source TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    )
    ''')
    
    # Images table
    cursor.execute('''
    CREATE TABLE images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        url TEXT NOT NULL,
        cloudflare_url TEXT,
        is_high_res BOOLEAN DEFAULT 0,
        is_main_image BOOLEAN DEFAULT 0,
        type TEXT DEFAULT 'product',
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    )
    ''')
    
    # Metadata table
    cursor.execute('''
    CREATE TABLE metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX idx_lego_sets_set_id ON lego_sets(set_id);")
    cursor.execute("CREATE INDEX idx_lego_sets_theme_id ON lego_sets(theme_id);")
    cursor.execute("CREATE INDEX idx_set_themes_set_id ON set_themes(set_id);")
    cursor.execute("CREATE INDEX idx_set_themes_theme_id ON set_themes(theme_id);")
    cursor.execute("CREATE INDEX idx_themes_parent_id ON themes(parent_id);")
    cursor.execute("CREATE INDEX idx_minifigures_set_id ON minifigures(set_id);")
    cursor.execute("CREATE INDEX idx_prices_set_id ON prices(set_id);")
    cursor.execute("CREATE INDEX idx_images_set_id ON images(set_id);")
    cursor.execute("CREATE INDEX idx_metadata_set_id ON metadata(set_id);")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database created successfully!")

def normalize_set_id(set_id: str) -> str:
    """Normalize a set ID to ensure consistent format."""
    if not set_id:
        return set_id
    
    # If the set ID doesn't have a dash, add -1 suffix
    if "-" not in set_id:
        return f"{set_id}-1"
    
    return set_id

def import_themes(db_path: str):
    """Import themes from the LEGO catalog."""
    print("Importing themes...")
    
    themes_file = os.path.join(LEGO_CATALOG_DIR, "themes.csv.gz")
    if not os.path.exists(themes_file):
        print(f"Themes file not found: {themes_file}")
        return {}
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load themes into a dictionary
    themes = {}
    theme_hierarchy = {}
    
    with gzip.open(themes_file, 'rt', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            theme_id = row.get('id')
            theme_name = row.get('name')
            parent_id = row.get('parent_id')
            
            if theme_id and theme_name:
                themes[theme_id] = theme_name
                
                # Insert into themes table
                cursor.execute('''
                INSERT INTO themes (id, name, parent_id)
                VALUES (?, ?, ?)
                ''', (
                    theme_id,
                    theme_name,
                    parent_id if parent_id else None
                ))
                
                # Store parent-child relationship
                if parent_id:
                    theme_hierarchy[theme_id] = parent_id
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"Imported {len(themes)} themes")
    return themes, theme_hierarchy

def get_theme_ancestors(theme_id: str, theme_hierarchy: Dict[str, str]) -> List[str]:
    """Get all ancestor theme IDs for a given theme."""
    ancestors = []
    current_id = theme_id
    
    while current_id in theme_hierarchy:
        parent_id = theme_hierarchy[current_id]
        ancestors.append(parent_id)
        current_id = parent_id
    
    return ancestors

def import_sets(db_path: str, themes_data: tuple):
    """Import sets from the LEGO catalog."""
    print("Importing sets...")
    
    themes, theme_hierarchy = themes_data
    
    sets_file = os.path.join(LEGO_CATALOG_DIR, "sets.csv.gz")
    if not os.path.exists(sets_file):
        print(f"Sets file not found: {sets_file}")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Import sets
    count = 0
    with gzip.open(sets_file, 'rt', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            set_num = row.get('set_num', '')
            name = row.get('name', '')
            year = row.get('year', None)
            theme_id = row.get('theme_id', None)
            num_parts = row.get('num_parts', 0)
            img_url = row.get('img_url', '')
            
            # Get theme name if theme_id is available
            theme_name = themes.get(theme_id) if theme_id else None
            
            # Normalize set ID
            set_id = normalize_set_id(set_num)
            
            # Insert into lego_sets table
            cursor.execute('''
            INSERT INTO lego_sets (set_id, set_num, name, year, theme_id, theme_name, num_parts, img_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                set_id,
                set_num,
                name,
                year,
                theme_id,
                theme_name,
                num_parts,
                img_url
            ))
            
            # Insert primary theme into set_themes junction table
            if theme_id:
                cursor.execute('''
                INSERT INTO set_themes (set_id, theme_id, is_primary)
                VALUES (?, ?, ?)
                ''', (
                    set_id,
                    theme_id,
                    1  # Primary theme
                ))
                
                # Insert ancestor themes into set_themes junction table
                ancestor_themes = get_theme_ancestors(theme_id, theme_hierarchy)
                for ancestor_id in ancestor_themes:
                    cursor.execute('''
                    INSERT INTO set_themes (set_id, theme_id, is_primary)
                    VALUES (?, ?, ?)
                    ''', (
                        set_id,
                        ancestor_id,
                        0  # Not primary theme
                    ))
            
            count += 1
            if count % 1000 == 0:
                print(f"Imported {count} sets...")
                conn.commit()
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Imported {count} sets successfully!")

def import_minifigs(db_path: str):
    """Import minifigures from the LEGO catalog."""
    print("Importing minifigures...")
    
    minifigs_file = os.path.join(LEGO_CATALOG_DIR, "minifigs.csv.gz")
    inventory_minifigs_file = os.path.join(LEGO_CATALOG_DIR, "inventory_minifigs.csv.gz")
    inventories_file = os.path.join(LEGO_CATALOG_DIR, "inventories.csv.gz")
    
    if not all(os.path.exists(f) for f in [minifigs_file, inventory_minifigs_file, inventories_file]):
        print("One or more minifigure files not found")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Load minifigures
    minifigs = {}
    with gzip.open(minifigs_file, 'rt', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            fig_num = row.get('fig_num')
            name = row.get('name')
            if fig_num and name:
                minifigs[fig_num] = name
    
    # Load inventories
    inventories = {}
    with gzip.open(inventories_file, 'rt', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            inventory_id = row.get('id')
            set_num = row.get('set_num')
            if inventory_id and set_num:
                inventories[inventory_id] = set_num
    
    # Import inventory minifigures
    count = 0
    with gzip.open(inventory_minifigs_file, 'rt', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            inventory_id = row.get('inventory_id')
            fig_num = row.get('fig_num')
            quantity = row.get('quantity', 1)
            
            if not inventory_id or not fig_num:
                continue
            
            set_num = inventories.get(inventory_id)
            name = minifigs.get(fig_num)
            
            if not set_num or not name:
                continue
            
            set_id = normalize_set_id(set_num)
            fig_id = f"{set_id}-{fig_num}"
            
            # Insert into minifigures table
            cursor.execute('''
            INSERT INTO minifigures (fig_id, set_id, name, count)
            VALUES (?, ?, ?, ?)
            ''', (
                fig_id,
                set_id,
                name,
                quantity
            ))
            
            count += 1
            if count % 1000 == 0:
                print(f"Imported {count} minifigures...")
                conn.commit()
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Imported {count} minifigures successfully!")

def import_images(db_path: str):
    """Import images from the LEGO catalog."""
    print("Importing images...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all sets with image URLs
    cursor.execute("SELECT set_id, img_url FROM lego_sets WHERE img_url IS NOT NULL AND img_url != ''")
    sets = cursor.fetchall()
    
    count = 0
    for set_id, img_url in sets:
        if not img_url:
            continue
        
        # Insert into images table
        cursor.execute('''
        INSERT INTO images (set_id, url, is_high_res, is_main_image, type)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            set_id,
            img_url,
            0,  # Not high-res
            1,  # Main image
            'product'
        ))
        
        count += 1
        if count % 1000 == 0:
            print(f"Imported {count} images...")
            conn.commit()
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Imported {count} images successfully!")

def main():
    parser = argparse.ArgumentParser(description="Create a clean SQLite database with LEGO catalog data")
    parser.add_argument("--force", action="store_true", help="Force recreation of the database if it exists")
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    ensure_output_dir()
    
    # Check if database already exists
    if os.path.exists(DATABASE_FILE) and not args.force:
        print(f"Database already exists at {DATABASE_FILE}")
        print("Use --force to recreate it")
        return
    
    # Create the database
    create_database(DATABASE_FILE)
    
    # Import data
    themes_data = import_themes(DATABASE_FILE)
    import_sets(DATABASE_FILE, themes_data)
    import_minifigs(DATABASE_FILE)
    import_images(DATABASE_FILE)
    
    print("\nDatabase creation and import completed!")
    print(f"Database file: {DATABASE_FILE}")

if __name__ == "__main__":
    main() 