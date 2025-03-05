#!/usr/bin/env python3
import os
import json
import re
import time
import random
import argparse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

# Constants
BASE_URL = "https://www.lego.com/nl-nl/categories/new-sets-and-products"
OUTPUT_DIR = "input"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "lego_urls.json")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def setup_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Ensured directory exists: {OUTPUT_DIR}")

def get_page(url: str, page_num: int = 1) -> Optional[str]:
    """Fetch the HTML content of a page."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.lego.com/nl-nl/",
        "Cache-Control": "no-cache"
    }
    
    # For pagination, simply add the page parameter to the URL
    paginated_url = url
    if page_num > 1:
        separator = '&' if '?' in url else '?'
        paginated_url = f"{url}{separator}page={page_num}"
    
    try:
        print(f"Fetching page {page_num}: {paginated_url}")
        response = requests.get(paginated_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching page {page_num}: {e}")
        return None

def extract_product_urls(html_content: str) -> List[str]:
    """Extract product URLs from the HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    product_urls = []
    
    # Look for product links - these typically have specific patterns
    # Based on the LEGO website structure, product links often contain "/product/" in the URL
    product_links = soup.find_all('a', href=lambda href: href and '/product/' in href)
    
    for link in product_links:
        product_url = urljoin("https://www.lego.com", link['href'])
        # Ensure we're only getting product pages
        if '/product/' in product_url and product_url not in product_urls:
            product_urls.append(product_url)
    
    print(f"Found {len(product_urls)} product URLs on this page")
    return product_urls

def get_max_page_number(html_content: str) -> int:
    """Extract the maximum page number from pagination."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try different approaches to find pagination
    # Method 1: Look for pagination elements with specific class names
    pagination_elements = soup.find_all(['a', 'span', 'div'], {'class': lambda x: x and any(c in x for c in ['Pagination', 'pagination', 'Page', 'page'])})
    
    # Method 2: Look for elements with page numbers
    page_number_pattern = re.compile(r'page=(\d+)')
    pagination_links = soup.find_all('a', href=lambda href: href and page_number_pattern.search(href))
    
    max_page = 1
    
    # Check pagination elements
    for element in pagination_elements:
        try:
            text = element.text.strip()
            if text.isdigit():
                max_page = max(max_page, int(text))
        except (ValueError, AttributeError):
            continue
    
    # Check pagination links
    for link in pagination_links:
        try:
            href = link.get('href', '')
            match = page_number_pattern.search(href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
        except (ValueError, AttributeError):
            continue
    
    # If we still haven't found pagination, let's try a more aggressive approach
    if max_page == 1:
        # Look for any numbers that might be page indicators
        number_elements = soup.find_all(text=re.compile(r'\d+'))
        for element in number_elements:
            try:
                text = element.strip()
                if text.isdigit() and 1 < int(text) <= 20:  # Reasonable page number range
                    max_page = max(max_page, int(text))
            except (ValueError, AttributeError):
                continue
    
    # If we still can't find pagination, default to a reasonable number
    if max_page == 1:
        print("Could not detect pagination. Setting max pages to 5 as a default.")
        return 5
    
    print(f"Detected maximum page number: {max_page}")
    return max_page

def scrape_all_pages(base_url: str, max_pages: Optional[int] = None) -> List[str]:
    """Scrape all pages of products."""
    all_product_urls = []
    
    # Get the first page
    first_page_html = get_page(base_url)
    if not first_page_html:
        print("Failed to fetch the first page. Exiting.")
        return []
    
    # Extract product URLs from the first page
    first_page_urls = extract_product_urls(first_page_html)
    all_product_urls.extend(first_page_urls)
    
    # Determine the maximum number of pages
    detected_max_pages = get_max_page_number(first_page_html)
    if max_pages is None:
        max_pages = detected_max_pages
    else:
        max_pages = min(max_pages, detected_max_pages)
    
    print(f"Will scrape up to {max_pages} pages")
    
    # Scrape remaining pages
    for page_num in range(2, max_pages + 1):
        # Add a delay to avoid overloading the server
        delay = random.uniform(1.5, 3.0)
        print(f"Waiting {delay:.2f} seconds before fetching next page...")
        time.sleep(delay)
        
        page_html = get_page(base_url, page_num)
        if not page_html:
            print(f"Failed to fetch page {page_num}. Continuing with next page.")
            continue
        
        page_urls = extract_product_urls(page_html)
        if not page_urls:
            print(f"No product URLs found on page {page_num}. This might be the last page.")
            break
            
        all_product_urls.extend(page_urls)
    
    # Remove duplicates while preserving order
    unique_urls = []
    for url in all_product_urls:
        if url not in unique_urls:
            unique_urls.append(url)
    
    return unique_urls

def save_urls_to_json(urls: List[str], output_file: str):
    """Save the list of URLs to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2)
    
    print(f"Saved {len(urls)} product URLs to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Scrape LEGO new products and save URLs to JSON")
    parser.add_argument("--max-pages", type=int, help="Maximum number of pages to scrape (default: all available)")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help=f"Output JSON file path (default: {OUTPUT_FILE})")
    parser.add_argument("--force", action="store_true", help="Force scrape even if pagination is not detected")
    args = parser.parse_args()
    
    print("Starting LEGO New Products Scraper")
    setup_directories()
    
    product_urls = scrape_all_pages(BASE_URL, args.max_pages)
    
    if product_urls:
        save_urls_to_json(product_urls, args.output)
        print(f"Successfully scraped {len(product_urls)} product URLs")
    else:
        print("No product URLs found")

if __name__ == "__main__":
    main() 