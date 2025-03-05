import json
import os
import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, List, Optional, Tuple
import re
from openai import OpenAI
import time
import concurrent.futures
import argparse
import sys
import random
import csv

# Load environment variables
load_dotenv()

# Create necessary directories if they don't exist
os.makedirs("input", exist_ok=True)
os.makedirs("output/products", exist_ok=True)
os.makedirs("output/raw", exist_ok=True)
os.makedirs("output/price_history", exist_ok=True)
os.makedirs("output/summaries", exist_ok=True)

# Path to the processed URLs tracking file
PROCESSED_URLS_FILE = "output/summaries/processed_urls.json"

# Oxylabs proxy configuration
OXYLABS_USERNAME = os.getenv("OXYLABS_USERNAME")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")
OXYLABS_ENDPOINT = os.getenv("OXYLABS_ENDPOINT", "dc.oxylabs.io")
try:
    OXYLABS_PORTS = [int(port.strip()) for port in os.getenv("OXYLABS_PORTS", "8001,8002,8003,8004,8005").split(",") if port.strip().isdigit()]
    if not OXYLABS_PORTS:  # Fallback if no valid ports
        OXYLABS_PORTS = [8001, 8002, 8003, 8004, 8005]
except Exception as e:
    print(f"Warning: Error parsing OXYLABS_PORTS: {e}. Using default ports.")
    OXYLABS_PORTS = [8001, 8002, 8003, 8004, 8005]

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Constants
OUTPUT_DIR = "output"
PRODUCTS_DIR = os.path.join(OUTPUT_DIR, "products")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
PRICE_HISTORY_DIR = os.path.join(OUTPUT_DIR, "price_history")
SUMMARIES_DIR = os.path.join(OUTPUT_DIR, "summaries")
INPUT_DIR = "input"
PROXIES_FILE = os.path.join(INPUT_DIR, "proxies.csv")
DEFAULT_TIMEOUT = 30  # Default timeout in seconds

class ProxyManager:
    """
    Manages a pool of proxies for rotation during requests.
    Tracks proxy success/failure and prioritizes working proxies.
    """
    def __init__(self, proxies_file: str = PROXIES_FILE, use_proxies: bool = False):
        self.proxies = []
        self.working_proxies = set()
        self.failed_proxies = {}
        self.use_proxies = use_proxies
        self.current_index = 0
        
        if use_proxies:
            self.load_proxies(proxies_file)
            self.add_oxylabs_proxies()
            print(f"Loaded {len(self.proxies)} proxies")
    
    def add_oxylabs_proxies(self):
        """Add Oxylabs proxies to the proxy pool if credentials are available"""
        if not OXYLABS_USERNAME or not OXYLABS_PASSWORD:
            return
        
        for port in OXYLABS_PORTS:
            proxy_url = f"http://user-{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_ENDPOINT}:{port}"
            if proxy_url not in self.proxies:
                self.proxies.append(proxy_url)
                print(f"Added Oxylabs proxy on port {port}")
    
    def load_proxies(self, proxies_file: str) -> None:
        """
        Load proxies from a CSV file.
        
        Args:
            proxies_file: Path to the CSV file containing proxy URLs
        """
        if not os.path.exists(proxies_file):
            print(f"Proxy file {proxies_file} not found. No proxies loaded.")
            return
        
        try:
            with open(proxies_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        proxy_url = row[0].strip()
                        if proxy_url not in self.proxies:
                            self.proxies.append(proxy_url)
        except Exception as e:
            print(f"Error loading proxies: {e}")
    
    def get_proxy(self) -> Dict[str, str]:
        """
        Get the next proxy in the rotation.
        Prioritizes working proxies over untested ones.
        
        Returns:
            Dictionary with proxy configuration for requests
        """
        if not self.use_proxies or not self.proxies:
            return {}
        
        # First try to use a working proxy if available
        if self.working_proxies:
            working_list = list(self.working_proxies)
            proxy_url = working_list[self.current_index % len(working_list)]
            self.current_index += 1
        else:
            # Otherwise, use the next proxy in the list, skipping known failed ones
            attempts = 0
            proxy_url = None
            
            while attempts < len(self.proxies):
                candidate = self.proxies[self.current_index % len(self.proxies)]
                self.current_index += 1
                
                # Skip proxies that have failed multiple times recently
                if candidate in self.failed_proxies and self.failed_proxies[candidate]["count"] > 2:
                    # Check if the failure is recent (within last hour)
                    last_failure = self.failed_proxies[candidate]["last_failure"]
                    if (datetime.datetime.now() - last_failure).total_seconds() < 3600:
                        attempts += 1
                        continue
                
                proxy_url = candidate
                break
            
            if proxy_url is None:
                return {}  # No suitable proxy found
        
        # Parse the proxy URL to get the scheme and actual proxy address
        try:
            if proxy_url.startswith(('http://', 'https://')):
                scheme = proxy_url.split('://')[0]
                return {scheme: proxy_url}
            else:
                return {'http': f'http://{proxy_url}', 'https': f'https://{proxy_url}'}
        except Exception as e:
            print(f"Error parsing proxy URL {proxy_url}: {e}")
            return {}
    
    def mark_proxy_success(self, proxy_url: str) -> None:
        """
        Mark a proxy as working.
        
        Args:
            proxy_url: The proxy URL that was successful
        """
        if not proxy_url or not self.use_proxies:
            return
        
        # Add to working proxies set
        self.working_proxies.add(proxy_url)
        
        # Remove from failed proxies if present
        if proxy_url in self.failed_proxies:
            del self.failed_proxies[proxy_url]
            
        print(f"Proxy {proxy_url} marked as working")
    
    def mark_proxy_failure(self, proxy_url: str) -> None:
        """
        Mark a proxy as failed.
        
        Args:
            proxy_url: The proxy URL that failed
        """
        if not proxy_url or not self.use_proxies:
            return
        
        # Remove from working proxies if present
        if proxy_url in self.working_proxies:
            self.working_proxies.remove(proxy_url)
        
        # Add to failed proxies with timestamp and increment failure count
        now = datetime.datetime.now()
        if proxy_url in self.failed_proxies:
            self.failed_proxies[proxy_url]["count"] += 1
            self.failed_proxies[proxy_url]["last_failure"] = now
        else:
            self.failed_proxies[proxy_url] = {
                "count": 1,
                "last_failure": now
            }
            
        print(f"Proxy {proxy_url} marked as failed (count: {self.failed_proxies[proxy_url]['count']})")

# Initialize the proxy manager
proxy_manager = None

def fetch_lego_product(url: str) -> Dict[str, Any]:
    """
    Fetch product information from a LEGO product page.
    
    Args:
        url: The URL of the LEGO product page
        
    Returns:
        Dictionary containing product information
    """
    global proxy_manager
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    result = {
        "url": url,
        "success": False,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Extract product ID from URL
    product_id_match = re.search(r'product/[^-]+-(\d+)', url)
    if not product_id_match:
        # Try alternative pattern
        product_id_match = re.search(r'product/([^/]+)(?:/|$)', url)
        if product_id_match:
            # Try to extract numeric part from the product name
            product_name = product_id_match.group(1)
            numeric_match = re.search(r'(\d+)', product_name)
            if numeric_match:
                product_id = numeric_match.group(1)
                result["product_id"] = product_id
            else:
                # Use the whole product name as ID if no numeric part
                result["product_id"] = product_name
        else:
            result["error"] = "Could not extract product ID from URL"
            return result
    else:
        product_id = product_id_match.group(1)
        result["product_id"] = product_id
    
    # Try to fetch the product page
    max_retries = 3
    retry_count = 0
    timeout = 30  # Default timeout
    
    if proxy_manager and proxy_manager.use_proxies:
        timeout = 60  # Longer timeout for proxy connections
    
    while retry_count < max_retries:
        try:
            current_proxy = {}
            current_proxy_url = None
            
            if proxy_manager and proxy_manager.use_proxies:
                current_proxy = proxy_manager.get_proxy()
                # Extract the proxy URL for tracking
                if current_proxy:
                    for scheme, proxy in current_proxy.items():
                        current_proxy_url = proxy
                        break
                    print(f"Using proxy: {current_proxy_url}")
                else:
                    print("No proxy available, using direct connection")
            
            response = requests.get(url, headers=headers, proxies=current_proxy, timeout=timeout)
            
            if response.status_code == 200:
                # Mark proxy as successful if used
                if current_proxy_url:
                    proxy_manager.mark_proxy_success(current_proxy_url)
                
                html = response.text
                soup = BeautifulSoup(html, 'lxml')
                
                # Extract product information
                result["html_title"] = soup.title.text.strip() if soup.title else ""
                
                # Extract JSON-LD data
                json_ld = None
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        if '@type' in data and data['@type'] == 'Product':
                            json_ld = data
                            break
                    except (json.JSONDecodeError, AttributeError):
                        continue
                
                if json_ld:
                    result["json_ld"] = json_ld
                    
                    # Extract basic product info from JSON-LD
                    result["title"] = json_ld.get('name', '')
                    
                    # Extract price
                    if 'offers' in json_ld:
                        offers = json_ld['offers']
                        if isinstance(offers, list) and offers:
                            offer = offers[0]
                        else:
                            offer = offers
                            
                        result["price"] = float(offer.get('price', 0))
                        result["currency"] = offer.get('priceCurrency', '')
                    
                    # Extract images
                    if 'image' in json_ld:
                        if isinstance(json_ld['image'], list):
                            result["images"] = json_ld['image']
                        else:
                            result["images"] = [json_ld['image']]
                
                # Extract meta tags
                meta_tags = {}
                for meta in soup.find_all('meta'):
                    if meta.get('property') or meta.get('name'):
                        key = meta.get('property') or meta.get('name')
                        value = meta.get('content')
                        if key and value:
                            meta_tags[key] = value
                
                result["meta_tags"] = meta_tags
                
                # Extract product details from meta tags
                if 'og:title' in meta_tags:
                    result["title"] = meta_tags['og:title']
                
                if 'og:image' in meta_tags and 'images' not in result:
                    result["images"] = [meta_tags['og:image']]
                
                # Extract structured data
                structured_data = []
                for script in soup.find_all('script', type='application/json'):
                    try:
                        data = json.loads(script.string)
                        structured_data.append(data)
                    except (json.JSONDecodeError, AttributeError):
                        continue
                
                result["structured_data"] = structured_data
                
                # Extract piece count from structured data
                if structured_data:
                    def search_json_for_piece_count(obj):
                        if isinstance(obj, dict):
                            # Check for piece count in various formats
                            for key, value in obj.items():
                                if key.lower() in ['piece count', 'pieces', 'piececount', 'piece_count']:
                                    try:
                                        return int(value)
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Check for piece count in nested objects
                                if isinstance(value, (dict, list)):
                                    result = search_json_for_piece_count(value)
                                    if result:
                                        return result
                                        
                                # Check for piece count in strings
                                if isinstance(value, str) and 'piece' in value.lower():
                                    match = re.search(r'(\d+)\s*pieces?', value.lower())
                                    if match:
                                        try:
                                            return int(match.group(1))
                                        except (ValueError, TypeError):
                                            pass
                        
                        elif isinstance(obj, list):
                            for item in obj:
                                result = search_json_for_piece_count(item)
                                if result:
                                    return result
                        
                        return None
                    
                    for data in structured_data:
                        piece_count = search_json_for_piece_count(data)
                        if piece_count:
                            result["piece_count"] = piece_count
                            break
                
                # Extract age range
                age_range = None
                for data in structured_data:
                    if isinstance(data, dict) and 'props' in data:
                        props = data.get('props', {})
                        page_props = props.get('pageProps', {})
                        
                        if 'productDetails' in page_props:
                            product_details = page_props.get('productDetails', {})
                            if 'ageRange' in product_details:
                                age_range = product_details.get('ageRange', {}).get('label', '')
                                break
                
                if age_range:
                    result["age_range"] = age_range
                
                # Count images
                image_count = 0
                if 'images' in result:
                    image_count = len(result['images'])
                
                print(f"Extracted product info for {url}:")
                print(f"  Title: {result.get('title', 'Unknown')}")
                print(f"  Price: {result.get('price', 'Unknown')} {result.get('currency', '')}")
                print(f"  Product ID: {result.get('product_id', 'Unknown')}")
                print(f"  Piece Count: {result.get('piece_count', 'Unknown')}")
                print(f"  Age Range: {result.get('age_range', 'Unknown')}")
                print(f"  Images: {image_count} found")
                
                result["success"] = True
                break
            else:
                print(f"Failed to fetch {url}: HTTP {response.status_code}")
                result["error"] = f"HTTP error: {response.status_code}"
                
                # Mark proxy as failed if used
                if current_proxy_url:
                    proxy_manager.mark_proxy_failure(current_proxy_url)
                
                retry_count += 1
                
        except requests.exceptions.ProxyError as e:
            print(f"Proxy error for {url}: {e}")
            result["error"] = f"Proxy error: {str(e)}"
            
            # Mark proxy as failed if used
            if current_proxy_url:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except requests.exceptions.Timeout as e:
            print(f"Timeout error for {url}: {e}")
            result["error"] = f"Timeout error: {str(e)}"
            
            # Mark proxy as failed if used
            if current_proxy_url:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            result["error"] = f"Request error: {str(e)}"
            
            # Mark proxy as failed if used
            if current_proxy_url:
                proxy_manager.mark_proxy_failure(current_proxy_url)
            
            retry_count += 1
            
        except Exception as e:
            print(f"Unexpected error for {url}: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
            retry_count += 1
        
        # Wait before retrying
        if retry_count < max_retries:
            time.sleep(2 * retry_count)  # Exponential backoff
    
    return result

def analyze_with_deepseek(product_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use DeepSeek API to generate markdown content in both English and Dutch for the product.
    
    Args:
        product_info: Dictionary containing the product information
        
    Returns:
        Dictionary with generated markdown content for the product
    """
    try:
        if not DEEPSEEK_API_KEY:
            print("No DeepSeek API key found. Returning placeholder content.")
            return {
                "markdown": {
                    "en": {
                        "title": product_info['basic_info']['title'],
                        "description": "Placeholder description - DeepSeek API key not configured.",
                        "features": "## Features\n- Placeholder features",
                        "specifications": "## Specifications\n- Placeholder specifications",
                        "gallery": "## Gallery\n- Placeholder gallery"
                    },
                    "nl": {
                        "title": product_info['basic_info']['title'],
                        "description": "Placeholder beschrijving - DeepSeek API sleutel niet geconfigureerd.",
                        "features": "## Kenmerken\n- Placeholder kenmerken",
                        "specifications": "## Specificaties\n- Placeholder specificaties",
                        "gallery": "## Galerij\n- Placeholder galerij"
                    }
                }
            }
        
        # Prepare headers for DeepSeek API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        # Prepare the request payload
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a LEGO product content writer with expertise in both English and Dutch languages. Create engaging markdown content for product pages. Return only the JSON object without any markdown code block markers."},
                {"role": "user", "content": f"""
                Create markdown content for this LEGO product in both English and Dutch.
                Use the following information to create engaging product descriptions:
                
                Title: {product_info['basic_info']['title']}
                Description: {product_info['basic_info'].get('description', 'No description available')}
                Price: {product_info['pricing']['current_price']['amount']} {product_info['pricing']['current_price']['currency']}
                Age Range: {product_info['basic_info'].get('age_range', 'Not specified')}
                Piece Count: {product_info['basic_info'].get('piece_count', 'Not specified')}
                
                Return ONLY the following JSON structure without any markdown code block markers:
                {{
                    "markdown": {{
                        "en": {{
                            "title": "Product title in English",
                            "description": "Main product description in English markdown",
                            "features": "## Features\\n- Feature list in English",
                            "specifications": "## Specifications\\n- Specs in English",
                            "gallery": "## Gallery\\nGallery information in English"
                        }},
                        "nl": {{
                            "title": "Product title in Dutch",
                            "description": "Main product description in Dutch markdown",
                            "features": "## Kenmerken\\n- Feature list in Dutch",
                            "specifications": "## Specificaties\\n- Specs in Dutch",
                            "gallery": "## Galerij\\nGallery information in Dutch"
                        }}
                    }}
                }}
                """
                }
            ]
        }
        
        print("Sending request to DeepSeek API...")
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error from DeepSeek API: {response.status_code} - {response.text}")
            return {
                "markdown": {
                    "en": {
                        "title": product_info['basic_info']['title'],
                        "description": f"Error generating content: {response.status_code}",
                        "features": "## Features\n- Error generating features",
                        "specifications": "## Specifications\n- Error generating specifications",
                        "gallery": "## Gallery\n- Error generating gallery"
                    },
                    "nl": {
                        "title": product_info['basic_info']['title'],
                        "description": f"Fout bij het genereren van inhoud: {response.status_code}",
                        "features": "## Kenmerken\n- Fout bij het genereren van kenmerken",
                        "specifications": "## Specificaties\n- Fout bij het genereren van specificaties",
                        "gallery": "## Galerij\n- Fout bij het genereren van galerij"
                    }
                }
            }
        
        # Parse the response
        response_data = response.json()
        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
        
        try:
            # Try to parse the content as JSON
            markdown_content = json.loads(content)
            return markdown_content
        except json.JSONDecodeError:
            # If the content is not valid JSON, try to extract JSON from it
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    markdown_content = json.loads(json_match.group(1))
                    return markdown_content
                except json.JSONDecodeError:
                    pass
            
            # If all else fails, return a placeholder
            print(f"Error parsing DeepSeek API response: {content[:100]}...")
            return {
                "markdown": {
                    "en": {
                        "title": product_info['basic_info']['title'],
                        "description": "Error parsing API response. Here's the raw content:\n\n" + content[:500],
                        "features": "## Features\n- Error parsing features",
                        "specifications": "## Specifications\n- Error parsing specifications",
                        "gallery": "## Gallery\n- Error parsing gallery"
                    },
                    "nl": {
                        "title": product_info['basic_info']['title'],
                        "description": "Fout bij het verwerken van API-antwoord. Hier is de ruwe inhoud:\n\n" + content[:500],
                        "features": "## Kenmerken\n- Fout bij het verwerken van kenmerken",
                        "specifications": "## Specificaties\n- Fout bij het verwerken van specificaties",
                        "gallery": "## Galerij\n- Fout bij het verwerken van galerij"
                    }
                }
            }
    
    except Exception as e:
        print(f"Error in analyze_with_deepseek: {str(e)}")
        return {
            "markdown": {
                "en": {
                    "title": product_info['basic_info']['title'],
                    "description": f"Error generating content: {str(e)}",
                    "features": "## Features\n- Error generating features",
                    "specifications": "## Specifications\n- Error generating specifications",
                    "gallery": "## Gallery\n- Error generating gallery"
                },
                "nl": {
                    "title": product_info['basic_info']['title'],
                    "description": f"Fout bij het genereren van inhoud: {str(e)}",
                    "features": "## Kenmerken\n- Fout bij het genereren van kenmerken",
                    "specifications": "## Specificaties\n- Fout bij het genereren van specificaties",
                    "gallery": "## Galerij\n- Fout bij het genereren van galerij"
                }
            }
        }

def load_price_history(product_id):
    """
    Load existing price history for a product if available.
    
    Args:
        product_id: The LEGO product ID
        
    Returns:
        A list of price history entries, each with date and price
    """
    history_file = f"output/price_history/price_history_{product_id}.json"
    
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading price history: {e}")
        return []

def update_price_history(product_id, current_price, currency):
    """
    Update the price history for a product with the current price.
    
    Args:
        product_id: The LEGO product ID
        current_price: The current price value
        currency: The currency of the price
        
    Returns:
        Updated price history list
    """
    # Load existing history
    price_history = load_price_history(product_id)
    
    # Add current price with timestamp
    current_time = datetime.datetime.now()
    price_entry = {
        "date": current_time.isoformat(),
        "price": current_price,
        "currency": currency
    }
    
    # Check if price has changed since last entry
    if price_history and price_history[-1]["price"] == current_price:
        # Update the last entry's date instead of adding a new one
        price_history[-1]["date"] = current_time.isoformat()
    else:
        # Add new entry if price changed or no history exists
        price_history.append(price_entry)
    
    # Save updated history
    history_file = f"output/price_history/price_history_{product_id}.json"
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(price_history, f, indent=2, ensure_ascii=False)
    
    return price_history

def load_processed_urls():
    """
    Load the list of already processed URLs.
    
    Returns:
        Dictionary with URLs as keys and processing info as values
    """
    if os.path.exists(PROCESSED_URLS_FILE):
        try:
            with open(PROCESSED_URLS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading processed URLs: {e}")
            return {}
    else:
        return {}

def update_processed_urls(url, result):
    """
    Update the list of processed URLs with a new entry.
    
    Args:
        url: The URL that was processed
        result: The processing result
    """
    processed_urls = load_processed_urls()
    
    # Add or update the entry for this URL
    processed_urls[url] = {
        "last_processed": datetime.datetime.now().isoformat(),
        "success": "success" in result and result["success"],
        "product_id": result.get("product_id", ""),
        "error": result.get("error", "") if "error" in result else ""
    }
    
    # Save the updated list
    with open(PROCESSED_URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(processed_urls, f, indent=2, ensure_ascii=False)

def process_url(url: str, skip_if_processed: bool = False) -> Dict[str, Any]:
    """
    Process a single URL: fetch product info, update price history, and generate content.
    
    Args:
        url: The URL of the LEGO product page
        skip_if_processed: Whether to skip processing if the URL has been processed before
        
    Returns:
        Dictionary containing the processed results
    """
    try:
        print(f"\n{'='*50}")
        print(f"Processing URL: {url}")
        print(f"{'='*50}")
        
        # Check if URL has been processed before
        if skip_if_processed:
            processed_urls = load_processed_urls()
            if url in processed_urls and processed_urls[url]["success"]:
                print(f"URL already processed successfully, skipping: {url}")
                return {
                    "success": True,
                    "product_id": processed_urls[url]["product_id"],
                    "skipped": True,
                    "url": url,
                    "timestamp": processed_urls[url]["last_processed"]
                }
        
        # Fetch product information
        product_data = fetch_lego_product(url)
        
        if not product_data.get("success", False):
            result = {
                "error": product_data.get("error", "Failed to fetch product information"),
                "url": url
            }
            update_processed_urls(url, result)
            print(f"Failed to process URL: {result['error']}")
            return result
        
        # Get product ID and current price
        product_id = product_data.get("product_id", "")
        if not product_id:
            result = {
                "error": "No product ID found",
                "url": url
            }
            update_processed_urls(url, result)
            print(f"Failed to process URL: No product ID found")
            return result
            
        # Extract price information
        price = product_data.get("price", 0)
        currency = product_data.get("currency", "EUR")
        
        # Update price history
        price_history = update_price_history(product_id, price, currency)
        
        # Add current scrape timestamp and price history to product info
        current_time = datetime.datetime.now()
        product_data['metadata'] = {
            'last_updated': current_time.isoformat(),
            'price_history': price_history
        }
        
        # Save raw product data for debugging
        with open(f"{RAW_DIR}/raw_lego_product_{product_id}.json", 'w', encoding='utf-8') as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)
        
        # Create a structured product data object for the AI
        structured_product_data = {
            'basic_info': {
                'title': product_data.get('title', ''),
                'product_id': product_id,
                'description': product_data.get('meta_tags', {}).get('og:description', ''),
                'age_range': product_data.get('age_range', ''),
                'piece_count': product_data.get('piece_count', 0),
                'brand': 'LEGO®',
                'condition': 'new',
                'locale': 'nl_NL'
            },
            'pricing': {
                'current_price': {
                    'amount': price,
                    'currency': currency
                },
                'special_offers': []
            },
            'images': product_data.get('images', [])
        }
        
        # Generate markdown content
        content = analyze_with_deepseek(structured_product_data)
        
        # Combine results
        results = {
            'content': content,
            'metadata': {
                'source_url': url,
                'scrape_date': current_time.isoformat(),
                'price_history': price_history
            }
        }
        
        # Save the results
        output_file = f"{PRODUCTS_DIR}/lego_product_{product_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Product markdown content saved to {output_file}")
        print(f"Price history saved with {len(price_history)} entries")
        
        result = {
            "success": True,
            "product_id": product_id,
            "url": url,
            "output_file": output_file,
            "timestamp": current_time.isoformat()
        }
        
        # Update processed URLs tracking
        update_processed_urls(url, result)
        
        return result
        
    except Exception as e:
        result = {
            "error": str(e),
            "url": url
        }
        update_processed_urls(url, result)
        print(f"Error processing URL {url}: {str(e)}")
        return result

def load_urls_from_json(json_file: str) -> List[str]:
    """
    Load URLs from a JSON file.
    
    Args:
        json_file: Path to the JSON file containing URLs
        
    Returns:
        List of URLs to process
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if the JSON contains a list of URLs directly
        if isinstance(data, list):
            urls = data
        # Or if it's a dictionary with a 'urls' key
        elif isinstance(data, dict) and 'urls' in data:
            urls = data['urls']
        else:
            raise ValueError("JSON file must contain either a list of URLs or a dictionary with a 'urls' key")
        
        # Validate that all items are strings (URLs)
        if not all(isinstance(url, str) for url in urls):
            raise ValueError("All items in the URL list must be strings")
        
        return urls
    
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading URLs from JSON file: {e}")
        return []

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Scrape LEGO product information from multiple URLs')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', help='Single LEGO product URL to scrape')
    group.add_argument('--file', help='JSON file containing a list of LEGO product URLs to scrape')
    group.add_argument('--list-processed', action='store_true', help='List all processed URLs and exit')
    
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of parallel workers')
    parser.add_argument('--skip-processed', action='store_true', help='Skip URLs that have been successfully processed before')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation for requests')
    parser.add_argument('--proxies-file', default=PROXIES_FILE, help='File containing proxy URLs')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    
    args = parser.parse_args()
    
    # Initialize the global proxy manager
    global proxy_manager
    proxy_manager = ProxyManager(proxies_file=args.proxies_file, use_proxies=args.use_proxies)
    
    # If requested, list processed URLs and exit
    if args.list_processed:
        processed_urls = load_processed_urls()
        if not processed_urls:
            print("No URLs have been processed yet.")
        else:
            print(f"Found {len(processed_urls)} processed URLs:")
            for url, info in processed_urls.items():
                status = "SUCCESS" if info.get("success", False) else "FAILED"
                product_id = info.get('product_id', 'Unknown')
                last_processed = info.get('last_processed', 'Unknown')
                print(f"[{status}] {url} (Product ID: {product_id}, Last processed: {last_processed})")
        return
    
    # Create necessary directories
    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PRICE_HISTORY_DIR, exist_ok=True)
    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    
    # Check if we have either a URL or a file
    if not args.url and not args.file:
        print("Error: You must provide either a URL (--url) or a JSON file with URLs (--file)")
        parser.print_help()
        sys.exit(1)
    
    # Process a single URL if provided
    if args.url:
        print(f"Processing single URL: {args.url}")
        result = process_url(args.url, args.skip_processed)
        if result.get('success', False):
            print(f"Successfully processed URL: {args.url}")
        else:
            print(f"Failed to process URL: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        return
    
    # Process multiple URLs from a file
    urls = load_urls_from_json(args.file)
    if not urls:
        print(f"No URLs found in {args.file}")
        sys.exit(1)
    
    print(f"Found {len(urls)} URLs to process")
    print(f"Processing with {args.max_workers} parallel workers")
    
    # Process URLs in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_url = {executor.submit(process_url, url, args.skip_processed): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
                if result.get('success', False):
                    if result.get('skipped', False):
                        print(f"Skipped already processed URL: {url}")
                    else:
                        print(f"Successfully processed {url}")
                else:
                    print(f"Failed to process {url}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.datetime.now().isoformat()
                })
    
    # Generate summary
    successful = [r for r in results if r.get('success', False) and not r.get('skipped', False)]
    failed = [r for r in results if not r.get('success', False)]
    skipped = [r for r in results if r.get('skipped', False)]
    
    print(f"\n{'='*50}")
    print(f"Processing complete: {len(successful)} successful, {len(skipped)} skipped, {len(failed)} failed")
    
    if failed:
        print("\nFailed URLs:")
        for result in failed:
            print(f"  {result['url']}: {result.get('error', 'Unknown error')}")
    
    if skipped:
        print("\nSkipped URLs:")
        for result in skipped:
            print(f"  {result['url']}")
    
    # Save summary
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S.%f")
    summary = {
        "timestamp": timestamp,
        "total_urls": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "skipped": len(skipped),
        "successful_urls": [r['url'] for r in successful],
        "failed_urls": [r['url'] for r in failed],
        "skipped_urls": [r['url'] for r in skipped]
    }
    
    summary_file = os.path.join(SUMMARIES_DIR, f"scrape_summary_{timestamp}.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Save latest summary
    latest_summary_file = os.path.join(SUMMARIES_DIR, "latest_summary.json")
    with open(latest_summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Summary report saved to {summary_file}")
    print(f"Latest summary saved to {latest_summary_file}")

if __name__ == "__main__":
    main()