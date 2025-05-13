"""
Simpler test for bathtub compatibility
"""

import requests
import traceback

# Simple test function
def test_sku(sku):
    print(f"\nTesting SKU: {sku}")
    url = "http://localhost:5000/search"
    payload = {"sku": sku}
    
    try:
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            print(f"  Success! Response length: {len(response.text)}")
            # Check if we got a "no product found" message
            if "No product found" in response.text:
                print("  Warning: No product found")
            # Check if we got any compatibility results
            elif "compatibilityData" in response.text:
                print("  Found compatibility data!")
                # Extract some basic info about the result
                import re
                product_name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', response.text)
                if product_name_match:
                    print(f"  Product: {product_name_match.group(1).strip()}")
                # Look for compatible categories
                categories_match = re.findall(r'data-category="([^"]+)"', response.text)
                if categories_match:
                    print(f"  Compatible categories: {', '.join(categories_match)}")
                else:
                    print("  No compatible categories found")
            else:
                print("  Warning: Response doesn't contain compatibility data")
            return True
        else:
            print(f"  Error! Status code: {response.status_code}")
            print(f"  Response: {response.text[:100]}...")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        traceback.print_exc()
        return False

# Simple test with a few SKUs
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