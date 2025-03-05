#!/usr/bin/env python3
import json
import os

def update_processed_urls():
    """Update processed URLs file with correct product IDs."""
    processed_urls_path = 'output/summaries/processed_urls.json'
    
    # ID mapping from old to new
    id_updates = {
        '1': '77251',
        '14': '10353',
        '20': '77243',
        '24': '42207',
        '499': '30709'
    }
    
    # Load the processed URLs file
    with open(processed_urls_path, 'r', encoding='utf-8') as f:
        processed_urls = json.load(f)
    
    # Update product IDs
    updated = False
    for url, data in processed_urls.items():
        old_id = data.get('product_id')
        if old_id in id_updates:
            new_id = id_updates[old_id]
            processed_urls[url]['product_id'] = new_id
            updated = True
            print(f'Updated {url} with new product ID: {old_id} -> {new_id}')
    
    # Save the updated file
    if updated:
        with open(processed_urls_path, 'w', encoding='utf-8') as f:
            json.dump(processed_urls, f, indent=2, ensure_ascii=False)
        print('Saved updated processed URLs file')
    else:
        print('No updates needed')

if __name__ == '__main__':
    update_processed_urls() 