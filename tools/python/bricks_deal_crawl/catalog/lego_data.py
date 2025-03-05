import json
import os
from dotenv import load_dotenv
import requests
from typing import Dict, Any, List
import re
from openai import OpenAI

# Load environment variables
load_dotenv()

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    raise ValueError("Please set DEEPSEEK_API_KEY in your .env file")

# Initialize OpenAI client with DeepSeek configuration
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def extract_product_info(data: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Extract relevant product information from the JSON data.
    """
    product_info = {}
    
    # Extract basic product information from metadata
    metadata = data.get('metadata', {})
    markdown_content = data.get('markdown', '')
    
    # Basic product details
    product_info['title'] = metadata.get('ogTitle', '').replace(' | Friends | Officiële LEGO® winkel NL', '')
    product_info['description'] = metadata.get('ogDescription', '')
    product_info['product_id'] = metadata.get('product:retailer_item_id', '')
    product_info['price'] = {
        'amount': float(metadata.get('product:price:amount', 0)),
        'currency': metadata.get('product:price:currency', '')
    }
    product_info['availability'] = metadata.get('product:availability', '')
    product_info['brand'] = metadata.get('product:brand', '')
    product_info['condition'] = metadata.get('product:condition', '')
    product_info['image_url'] = metadata.get('ogImage', '')
    product_info['url'] = metadata.get('url', '')
    
    # Extract additional information from markdown content
    product_info.update(extract_from_markdown(markdown_content))
    
    return product_info

def extract_from_markdown(content: str) -> Dict[str, Any]:
    """
    Extract additional product information from markdown content.
    """
    additional_info = {
        'age_range': '',
        'piece_count': 0,
        'features': [],
        'special_offers': [],
        'rating': {
            'score': 0.0,
            'count': 0
        },
        'insiders_points': 0,
        'included_items': [],
        'product_details': [],
        'recommended_products': [],
        'gifts_with_purchase': []
    }
    
    # Extract age range
    age_match = re.search(r'Leeftijden:\s*(\d+\+)', content)
    if age_match:
        additional_info['age_range'] = age_match.group(1)
    
    # Extract piece count
    pieces_match = re.search(r'Stenen:\s*(\d+)', content)
    if pieces_match:
        additional_info['piece_count'] = int(pieces_match.group(1))
    
    # Extract LEGO Insiders points
    points_match = re.search(r'LEGO® Insiders-punten:\s*(\d+)', content)
    if points_match:
        additional_info['insiders_points'] = int(points_match.group(1))
    
    # Extract rating information
    rating_match = re.search(r'Average rating(\d+\.?\d*)\s*out of 5 stars', content)
    reviews_match = re.search(r'(\d+)\s*Recensies', content)
    if rating_match:
        additional_info['rating']['score'] = float(rating_match.group(1))
    if reviews_match:
        additional_info['rating']['count'] = int(reviews_match.group(1))
    
    # Extract features from sections
    sections = re.findall(r'### ([^\n]+)(?:\n+([^#]+))?', content, re.DOTALL)
    for title, content in sections:
        title = title.strip()
        if content:
            content = content.strip()
            if 'verassingen' in title.lower() or 'activiteiten' in title.lower():
                additional_info['features'].append({'title': title, 'description': content})
    
    # Extract special offers
    if 'Opruiming' in content:
        discount_match = re.search(r'\\- (\d+)%', content)
        if discount_match:
            additional_info['special_offers'].append({
                'type': 'discount',
                'value': f"{discount_match.group(1)}%",
                'description': 'Opruiming korting'
            })
    
    # Extract gifts with purchase
    gifts_section = re.findall(r'Cadeaus bij aankoop[^#]*?Geldig voor[^#]*?(\d{2}-\d{2}-\d{4})', content, re.DOTALL)
    if gifts_section:
        additional_info['gifts_with_purchase'].append({
            'description': 'Ferrari 499P – hypercar',
            'end_date': gifts_section[0]
        })
    
    # Extract recommended products
    recommended_section = re.findall(r'Aanbevolen voor jou[^#]*((?:\*\*[^\*]+\*\*[^#]+)+)', content, re.DOTALL)
    if recommended_section:
        products = re.findall(r'\*\*([^\*]+)\*\*\s*(?:\€(\d+\.\d+))?', recommended_section[0])
        additional_info['recommended_products'] = [
            {'name': name.strip(), 'price': price} for name, price in products if name.strip()
        ]
    
    return additional_info

def analyze_with_deepseek(product_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use DeepSeek API to analyze the product information and extract additional insights.
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a LEGO product analysis expert."},
                {"role": "user", "content": f"""
                Analyze this LEGO product and provide insights in JSON format:
                
                Product: {product_info['title']}
                Description: {product_info['description']}
                Age Range: {product_info['age_range']}
                Pieces: {product_info['piece_count']}
                Price: {product_info['price']['amount']} {product_info['price']['currency']}
                Features: {json.dumps(product_info['features'], ensure_ascii=False)}
                """}
            ],
            temperature=0.7,
            stream=False
        )
        return {
            "choices": [{
                "message": {
                    "content": response.choices[0].message.content
                }
            }]
        }
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return {}

def format_output(product_info: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the final output combining product information and analysis.
    """
    return {
        'product': {
            'basic_info': {
                'title': product_info['title'],
                'product_id': product_info['product_id'],
                'description': product_info['description'],
                'age_range': product_info['age_range'],
                'piece_count': product_info['piece_count'],
                'insiders_points': product_info.get('insiders_points', 0)
            },
            'pricing': {
                'current_price': product_info['price'],
                'special_offers': product_info['special_offers']
            },
            'ratings': product_info['rating'],
            'features': product_info['features'],
            'media': {
                'image_url': product_info['image_url'],
                'product_url': product_info['url']
            },
            'additional_info': {
                'gifts_with_purchase': product_info.get('gifts_with_purchase', []),
                'recommended_products': product_info.get('recommended_products', [])
            }
        },
        'analysis': analysis.get('choices', [{}])[0].get('message', {}).get('content', ''),
        'metadata': {
            'brand': product_info['brand'],
            'condition': product_info['condition'],
            'availability': product_info['availability']
        }
    }

def main():
    # Read the JSON file
    with open('results.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Process each item in the JSON array
    for item in data:
        # Extract basic product information
        product_info = extract_product_info(item)
        
        # Analyze with DeepSeek API
        analysis = analyze_with_deepseek(product_info)
        
        # Format the final output
        results = format_output(product_info, analysis)
        
        # Save the processed results
        output_file = f"processed_lego_{product_info['product_id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Processed data saved to {output_file}")

if __name__ == "__main__":
    main() 