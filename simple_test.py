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