"""
Simpler test for bathtub compatibility
"""

import requests
import traceback
import re
import json

# Simple test function
def test_sku(sku):
    print(f"\nTesting SKU: {sku}")
    url = "http://localhost:5000/search"
    payload = {"sku": sku}
    
    try:
        response = requests.post(url, data=payload)
        
        print(f"  Success! Response length: {len(response.text)}")
        
        # Check if we got a "no product found" message
        if "No product found" in response.text:
            print("  Warning: No product found")
            return True
            
        # Save response to a file for analysis
        with open(f"response_{sku}.html", "w") as f:
            f.write(response.text)
        print(f"  Response saved to response_{sku}.html")
        
        # Extract the title to identify the product
        product_name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', response.text)
        if product_name_match:
            print(f"  Product: {product_name_match.group(1).strip()}")
            
        # Try to parse as JSON first
        try:
            data = json.loads(response.text)
            if data.get('success') == True:
                print("  Success! Found JSON response with valid data")
                product = data.get('product', {})
                print(f"  Product details: SKU={product.get('sku')}, Name={product.get('name')}, Category={product.get('category')}")
                
                compatibles = data.get('compatibles', [])
                if compatibles:
                    print(f"  Found {len(compatibles)} compatible categories:")
                    for category in compatibles:
                        print(f"    - {category.get('category')}: {len(category.get('products', []))} products")
                else:
                    print("  No compatible products found in data")
            else:
                print(f"  JSON response indicates failure: {data.get('message', 'No message provided')}")
                
        except json.JSONDecodeError:
            # Not JSON, try HTML/JavaScript format
            print("  Not a JSON response, checking for HTML/JavaScript format")
            
            # Check if we have compatibility data
            if "var compatibilityData" in response.text:
                print("  Found compatibilityData variable in response")
                
                # Try to extract the JSON data
                json_match = re.search(r'var\s+compatibilityData\s*=\s*({.*?});', response.text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        product = data.get('product', {})
                        print(f"  Product details: SKU={product.get('sku')}, Name={product.get('name')}")
                        
                        compatibles = data.get('compatibles', [])
                        if compatibles:
                            print(f"  Found {len(compatibles)} compatible categories:")
                            for category in compatibles:
                                print(f"    - {category.get('category')}: {len(category.get('products', []))} products")
                        else:
                            print("  No compatible products found in data")
                    except json.JSONDecodeError:
                        print("  Error parsing JSON data")
            else:
                print("  No compatibilityData variable found")
                
                # Check for other key elements
                if "<form" in response.text:
                    print("  Contains a form element")
                if "No compatible products found" in response.text:
                    print("  Contains 'No compatible products found' message")
                if "product-details" in response.text:
                    print("  Contains product details section")
                    
                # Try to get page title
                title_match = re.search(r'<title>([^<]+)</title>', response.text)
                if title_match:
                    print(f"  Page title: {title_match.group(1).strip()}")
                
        return True
        
    except Exception as e:
        print(f"  Exception: {e}")
        traceback.print_exc()
        return False
        
# Test with a few SKUs
if __name__ == "__main__":
    # Test with different types of products
    skus = [
        "105821",  # Bathtub
        "106668",  # Bathtub
        "203010",  # Try a base
        "DW244876",  # Try a door
    ]
    
    for sku in skus:
        test_sku(sku)