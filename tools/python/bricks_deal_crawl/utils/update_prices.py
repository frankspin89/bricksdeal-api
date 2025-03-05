#!/usr/bin/env python3
import os
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Import functions from existing scripts
from bricks_deal_crawl.scrapers.lego_direct import fetch_lego_product, load_price_history, update_price_history, ProxyManager
from bricks_deal_crawl.scrapers.new_products import setup_directories

# Constants
PRODUCTS_DIR = os.path.join("output", "products")
PRICE_CHANGES_DIR = os.path.join("output", "price_changes")
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def load_all_product_ids() -> List[str]:
    """Load all product IDs from the products directory."""
    product_ids = []
    
    if not os.path.exists(PRODUCTS_DIR):
        print(f"Products directory not found: {PRODUCTS_DIR}")
        return product_ids
    
    for filename in os.listdir(PRODUCTS_DIR):
        if filename.startswith("lego_product_") and filename.endswith(".json"):
            product_id = filename.replace("lego_product_", "").replace(".json", "")
            product_ids.append(product_id)
    
    return product_ids

def get_product_url(product_id: str) -> Optional[str]:
    """Get the source URL for a product from its JSON file."""
    product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
    
    if not os.path.exists(product_path):
        print(f"Product file not found: {product_path}")
        return None
    
    try:
        with open(product_path, 'r', encoding='utf-8') as f:
            product_data = json.load(f)
        
        # Check if the product data has a nested structure
        if "product" in product_data:
            product_info = product_data["product"]
        else:
            product_info = product_data
            
        # Get the source URL from metadata
        if "metadata" in product_data and "source_url" in product_data["metadata"]:
            return product_data["metadata"]["source_url"]
        
        return None
    except Exception as e:
        print(f"Error loading product {product_id}: {e}")
        return None

def check_product_price(product_id: str, proxy_manager: Optional[ProxyManager] = None) -> Tuple[bool, Dict[str, Any]]:
    """Check the current price of a product and update its price history."""
    product_url = get_product_url(product_id)
    if not product_url:
        return False, {"error": "No source URL found"}
    
    # Load existing price history
    price_history = load_price_history(product_id)
    
    # Get the latest price
    for attempt in range(MAX_RETRIES):
        try:
            # The fetch_lego_product function doesn't accept a proxy parameter
            # so we're not using proxies for now
            product_data = fetch_lego_product(product_url)
            
            # Check if we have a valid product data
            if not product_data:
                time.sleep(RETRY_DELAY)
                continue
            
            # Extract price information
            current_price = None
            currency = None
            
            # Try to get price from product data
            if "product" in product_data:
                product_info = product_data["product"]
            else:
                product_info = product_data
                
            if "price" in product_info:
                current_price = product_info["price"].get("amount")
                currency = product_info["price"].get("currency", "EUR")
            else:
                # Try to find price in other locations
                if "metadata" in product_data and "price" in product_data["metadata"]:
                    current_price = product_data["metadata"]["price"].get("amount")
                    currency = product_data["metadata"]["price"].get("currency", "EUR")
                
                # Try to find price in meta tags
                if "meta_tags" in product_data and not current_price:
                    meta_tags = product_data["meta_tags"]
                    
                    if isinstance(meta_tags, list):
                        # Check for og:price:amount
                        og_price_amount = next((tag.get("content") for tag in meta_tags if isinstance(tag, dict) and tag.get("property") == "og:price:amount"), None)
                        og_price_currency = next((tag.get("content") for tag in meta_tags if isinstance(tag, dict) and tag.get("property") == "og:price:currency"), "EUR")
                        
                        if og_price_amount:
                            try:
                                current_price = float(og_price_amount)
                                currency = og_price_currency
                            except (ValueError, TypeError):
                                pass
                        
                        # Check for product:price:amount
                        if not current_price:
                            product_price_amount = next((tag.get("content") for tag in meta_tags if isinstance(tag, dict) and tag.get("property") == "product:price:amount"), None)
                            product_price_currency = next((tag.get("content") for tag in meta_tags if isinstance(tag, dict) and tag.get("property") == "product:price:currency"), "EUR")
                            
                            if product_price_amount:
                                try:
                                    current_price = float(product_price_amount)
                                    currency = product_price_currency
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(meta_tags, dict):
                        # Handle meta tags as a dictionary
                        for key, value in meta_tags.items():
                            if "price" in key.lower() and "amount" in key.lower():
                                try:
                                    current_price = float(value)
                                    currency = "EUR"  # Default currency
                                    break
                                except (ValueError, TypeError):
                                    pass
            
            # Try to find price in structured data
            if "structured_data" in product_data and not current_price:
                structured_data = product_data["structured_data"]
                
                # Check if structured_data is a list (sometimes it's a list of dicts)
                if isinstance(structured_data, list) and structured_data:
                    for item in structured_data:
                        if isinstance(item, dict):
                            if "offers" in item:
                                offers = item["offers"]
                                if isinstance(offers, dict) and "price" in offers:
                                    try:
                                        current_price = float(offers["price"])
                                        currency = offers.get("priceCurrency", "EUR")
                                        break
                                    except (ValueError, TypeError):
                                        pass
                
                # Check if structured_data is a dict
                elif isinstance(structured_data, dict):
                    if "offers" in structured_data:
                        offers = structured_data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            try:
                                current_price = float(offers["price"])
                                currency = offers.get("priceCurrency", "EUR")
                            except (ValueError, TypeError):
                                pass
                    
                    # Sometimes the price is nested in @graph
                    elif "@graph" in structured_data:
                        graph = structured_data["@graph"]
                        for item in graph:
                            if isinstance(item, dict):
                                if "offers" in item:
                                    offers = item["offers"]
                                    if isinstance(offers, dict) and "price" in offers:
                                        try:
                                            current_price = float(offers["price"])
                                            currency = offers.get("priceCurrency", "EUR")
                                            break
                                        except (ValueError, TypeError):
                                            pass
            
            # If price found, update price history
            if current_price is not None:
                print(f"Found price: {current_price} {currency}")
                # Update price history
                updated_history = update_price_history(product_id, current_price, currency)
                
                # Update the product file with the new price and price history
                product_path = os.path.join(PRODUCTS_DIR, f"lego_product_{product_id}.json")
                with open(product_path, 'r', encoding='utf-8') as f:
                    full_product_data = json.load(f)
                
                # Check if the product data has a nested structure
                if "product" in full_product_data:
                    if "price" not in full_product_data["product"]:
                        full_product_data["product"]["price"] = {}
                    full_product_data["product"]["price"]["amount"] = current_price
                    full_product_data["product"]["price"]["currency"] = currency
                    full_product_data["metadata"]["price_history"] = updated_history
                else:
                    if "price" not in full_product_data:
                        full_product_data["price"] = {}
                    full_product_data["price"]["amount"] = current_price
                    full_product_data["price"]["currency"] = currency
                    if "metadata" not in full_product_data:
                        full_product_data["metadata"] = {}
                    full_product_data["metadata"]["price_history"] = updated_history
                
                # Save updated product data
                with open(product_path, 'w', encoding='utf-8') as f:
                    json.dump(full_product_data, f, indent=2, ensure_ascii=False)
                
                return True, {
                    "product_id": product_id,
                    "current_price": current_price,
                    "currency": currency,
                    "price_history": updated_history
                }
            else:
                return False, {"error": "No price found in product data"}
                
        except Exception as e:
            print(f"Error checking price for product {product_id} (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
    
    return False, {"error": f"Failed after {MAX_RETRIES} attempts"}

def generate_price_change_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a report of price changes."""
    today = datetime.now().strftime("%Y-%m-%d")
    report = {
        "date": today,
        "total_products": len(results),
        "successful_updates": sum(1 for r in results if r.get("success", False)),
        "failed_updates": sum(1 for r in results if not r.get("success", False)),
        "price_changes": [],
        "errors": []
    }
    
    for result in results:
        if result.get("success", False):
            data = result.get("data", {})
            product_id = data.get("product_id")
            price_history = data.get("price_history", [])
            
            # Check if we have at least 2 price points to compare
            if len(price_history) >= 2:
                latest = price_history[-1]
                previous = price_history[-2]
                
                if latest["price"] != previous["price"]:
                    change_amount = latest["price"] - previous["price"]
                    # Avoid division by zero
                    change_percent = 0
                    if previous["price"] > 0:
                        change_percent = round(change_amount / previous["price"] * 100, 2)
                    
                    change = {
                        "product_id": product_id,
                        "previous_price": previous["price"],
                        "current_price": latest["price"],
                        "currency": data.get("currency", "EUR"),
                        "change_amount": change_amount,
                        "change_percent": change_percent,
                        "previous_date": previous["date"],
                        "current_date": latest["date"]
                    }
                    report["price_changes"].append(change)
        else:
            report["errors"].append({
                "product_id": result.get("product_id"),
                "error": result.get("data", {}).get("error", "Unknown error")
            })
    
    # Save the report
    os.makedirs(PRICE_CHANGES_DIR, exist_ok=True)
    report_path = os.path.join(PRICE_CHANGES_DIR, f"price_changes_{today}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report

def update_all_prices(product_ids: Optional[List[str]] = None, use_proxies: bool = False, max_workers: int = 5) -> Dict[str, Any]:
    """Update prices for all products or a specific list of product IDs."""
    setup_directories()
    
    # Create price changes directory if it doesn't exist
    os.makedirs(PRICE_CHANGES_DIR, exist_ok=True)
    
    # If no product IDs provided, load all product IDs
    if not product_ids:
        product_ids = load_all_product_ids()
    
    if not product_ids:
        print("No products found to update.")
        return {"error": "No products found"}
    
    print(f"Updating prices for {len(product_ids)} products...")
    
    # Note: We're not using proxies for now as fetch_lego_product doesn't support them
    results = []
    
    # Use ThreadPoolExecutor to check prices in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_product_price, product_id, None): product_id for product_id in product_ids}
        
        for future in tqdm(futures, desc="Checking prices", unit="product"):
            product_id = futures[future]
            try:
                success, data = future.result()
                results.append({
                    "product_id": product_id,
                    "success": success,
                    "data": data
                })
            except Exception as e:
                print(f"Error processing product {product_id}: {e}")
                results.append({
                    "product_id": product_id,
                    "success": False,
                    "data": {"error": str(e)}
                })
    
    # Generate and print report
    report = generate_price_change_report(results)
    
    print(f"\nPrice update completed:")
    print(f"- Total products: {report['total_products']}")
    print(f"- Successful updates: {report['successful_updates']}")
    print(f"- Failed updates: {report['failed_updates']}")
    print(f"- Products with price changes: {len(report['price_changes'])}")
    
    if report['price_changes']:
        print("\nPrice changes detected:")
        for change in report['price_changes']:
            direction = "increased" if change['change_amount'] > 0 else "decreased"
            print(f"- Product {change['product_id']}: {direction} by {abs(change['change_amount'])} {change['currency']} ({change['change_percent']}%)")
    
    if report['errors']:
        print("\nErrors:")
        for error in report['errors'][:5]:  # Show only first 5 errors
            print(f"- Product {error['product_id']}: {error['error']}")
        if len(report['errors']) > 5:
            print(f"  ... and {len(report['errors']) - 5} more errors")
    
    return report

def main():
    parser = argparse.ArgumentParser(description="Update prices for LEGO products")
    parser.add_argument("--product-ids", nargs="+", help="Specific product IDs to update")
    parser.add_argument("--use-proxies", action="store_true", help="Use proxies for requests")
    parser.add_argument("--max-workers", type=int, default=5, help="Maximum number of parallel workers")
    
    args = parser.parse_args()
    
    update_all_prices(
        product_ids=args.product_ids,
        use_proxies=args.use_proxies,
        max_workers=args.max_workers
    )

if __name__ == "__main__":
    main() 