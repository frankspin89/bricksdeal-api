#!/usr/bin/env python3

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Oxylabs credentials from environment variables
OXYLABS_USERNAME = os.environ.get("OXYLABS_USERNAME")
OXYLABS_PASSWORD = os.environ.get("OXYLABS_PASSWORD")

# Check if credentials are available
if not OXYLABS_USERNAME or not OXYLABS_PASSWORD:
    print("Error: Oxylabs credentials not found in environment variables.")
    print("Please set OXYLABS_USERNAME and OXYLABS_PASSWORD environment variables.")
    exit(1)

# Add 'user-' prefix if not already present
if not OXYLABS_USERNAME.startswith("user-"):
    OXYLABS_USERNAME = f"user-{OXYLABS_USERNAME}"

print(f"Using Oxylabs username: {OXYLABS_USERNAME}")

# Test with different proxy configurations
def test_proxy(proxy_url, proxy_type="datacenter"):
    """Test a proxy configuration with Oxylabs test URL."""
    print(f"\nTesting {proxy_type} proxy: {proxy_url}")
    
    # Create proxy configuration
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    print(f"Proxy configuration: {proxies}")
    
    # Set up headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    try:
        # Make request with proxy to Oxylabs' test URL
        print("Making request to https://ip.oxylabs.io/location...")
        response = requests.get("https://ip.oxylabs.io/location", proxies=proxies, timeout=20)
        response.raise_for_status()
        
        # Print response
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        print(f"✅ Proxy test successful for {proxy_url}")
        return True
        
    except Exception as e:
        print(f"❌ Proxy test failed for {proxy_url}: {str(e)}")
        return False

# Test with Datacenter Proxies
print("\n=== Testing Datacenter Proxies ===")
datacenter_proxy = f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@dc.oxylabs.io:8000"
test_proxy(datacenter_proxy, "datacenter")

# Test with country-specific Datacenter Proxies
print("\n=== Testing Country-specific Datacenter Proxies ===")
if "-country-" not in OXYLABS_USERNAME:
    country_username = OXYLABS_USERNAME + "-country-us"
else:
    country_username = OXYLABS_USERNAME
country_dc_proxy = f"http://{country_username}:{OXYLABS_PASSWORD}@dc.oxylabs.io:8000"
test_proxy(country_dc_proxy, "country-specific datacenter")

print("\nProxy testing completed.") 