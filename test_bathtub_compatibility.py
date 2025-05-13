"""
Test script for bathtub compatibility
"""

import requests
import json

# First, let's get a list of bathtub SKUs to test with
def get_bathtub_skus():
    url = "http://localhost:5000/suggest_skus?query=bath"
    response = requests.get(url)
    
    if response.status_code == 200:
        suggestions = response.json()
        # Filter for bathtub SKUs
        bathtub_skus = [suggestion.split(' - ')[0] for suggestion in suggestions 
                        if 'bath' in suggestion.lower()]
        return bathtub_skus[:5]  # Return up to 5 bathtub SKUs
    else:
        print(f"Error getting suggestions: {response.status_code}")
        return []

# Test compatibility search for bathtubs
def test_bathtub_compatibility(sku):
    url = "http://localhost:5000/search"
    payload = {"sku": sku}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=payload, headers=headers)
    
    if response.status_code == 200:
        # Extract JSON data from the HTML response
        html = response.text
        start_index = html.find('var compatibilityData = ') + len('var compatibilityData = ')
        end_index = html.find('};', start_index) + 1
        json_string = html[start_index:end_index]
        
        try:
            # Direct JSON response from the server
            data = response.json()
            print(f"\nCompatibility data for SKU {sku}:")
            print(f"Product name: {data.get('product', {}).get('name', 'N/A')}")
            
            # Check for compatible products
            compatible_categories = data.get("compatibles", [])
            if compatible_categories:
                for category in compatible_categories:
                    print(f"\nCompatible {category['category']} ({len(category['products'])} items):")
                    for i, product in enumerate(category['products'][:3]):  # Show up to 3 products
                        print(f"  {i+1}. {product.get('sku')} - {product.get('name')}")
                    if len(category['products']) > 3:
                        print(f"  ... and {len(category['products']) - 3} more")
            else:
                print("No compatible products found.")
                
            return True
        except Exception as e:
            print(f"Error parsing response: {e}")
            return False
    else:
        print(f"Error searching for SKU {sku}: {response.status_code}")
        return False

if __name__ == "__main__":
    print("Testing bathtub compatibility...")
    bathtub_skus = get_bathtub_skus()
    
    if not bathtub_skus:
        print("No bathtub SKUs found, using hardcoded values")
        # Use the first few bathtub SKUs we saw in the dataset
        bathtub_skus = ["105821", "106668", "106227"]
    
    print(f"Testing with bathtub SKUs: {bathtub_skus}")
    
    for sku in bathtub_skus:
        test_bathtub_compatibility(sku)