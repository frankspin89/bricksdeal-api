#!/usr/bin/env python3

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Oxylabs credentials from environment variables
username = os.environ.get("OXYLABS_USERNAME", "")
password = os.environ.get("OXYLABS_PASSWORD", "")

# Add 'user-' prefix if not already present
if not username.startswith("user-"):
    username = f"user-{username}"

print(f"Username: {username}")

# Simple test with Oxylabs documentation example
proxies = {
    "http": f"http://{username}:{password}@dc.oxylabs.io:8000",
    "https": f"http://{username}:{password}@dc.oxylabs.io:8000"
}

print(f"Proxies: {proxies}")

try:
    print("Making request to http://ip.oxylabs.io...")
    response = requests.get("http://ip.oxylabs.io", proxies=proxies, timeout=10)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}") 