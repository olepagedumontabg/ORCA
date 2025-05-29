#!/usr/bin/env python3
"""
Test script to verify whitelist override functionality for bathtub incompatibility reasons
"""

import requests
import json

def test_whitelist_override():
    """Test the whitelist override functionality"""
    
    # Test SKU that has incompatibility reasons for Tub Doors
    test_sku = "105546"
    
    print(f"Testing whitelist override for SKU: {test_sku}")
    print("=" * 50)
    
    # Make API call to search for the SKU
    url = "http://localhost:5000/search"
    payload = {"sku": test_sku}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            
            print("Current results:")
            print(f"Success: {data.get('success', False)}")
            
            if data.get('incompatibility_reasons'):
                print("\nIncompatibility reasons:")
                for category, reason in data['incompatibility_reasons'].items():
                    print(f"  {category}: {reason}")
            
            print("\nCompatible categories:")
            for category in data.get('compatibles', []):
                if 'reason' in category:
                    print(f"  {category['category']}: INCOMPATIBLE - {category['reason']}")
                else:
                    print(f"  {category['category']}: {len(category.get('products', []))} products")
            
            print("\nWhitelist override behavior:")
            print("- If you add a Tub Door SKU to the whitelist for this bathtub,")
            print("  the incompatibility reason will be replaced with the whitelisted door(s)")
            print("- The incompatibility message will disappear")
            print("- The whitelisted door(s) will appear as compatible products")
            
        else:
            print(f"API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_whitelist_override()