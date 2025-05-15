#!/usr/bin/env python
"""
Test script for door backward compatibility search.
This script tests the ability to find compatible shower bases and bathtubs for a given door.
"""

import requests
import json
import sys

def test_door_compatibility(door_sku):
    """
    Test the backward compatibility search for a door.
    Finds which shower bases or bathtubs are compatible with the specified door.
    """
    print(f"Testing backward compatibility for door SKU: {door_sku}")
    
    try:
        # Call the search API
        response = requests.post('http://localhost:5000/search', data={'sku': door_sku})
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if data.get('success', False):
                    print("\n✅ Door found successfully")
                    
                    # Print door details
                    door_info = data.get('product', {})
                    print(f"\nDoor Details:")
                    print(f"  SKU: {door_info.get('sku')}")
                    print(f"  Name: {door_info.get('name')}")
                    print(f"  Category: {door_info.get('category')}")
                    print(f"  Min Width: {door_info.get('min_width')}")
                    print(f"  Max Width: {door_info.get('max_width')}")
                    
                    # Check for compatible products
                    compatible_products = data.get('compatibles', [])
                    print(f"\nFound {len(compatible_products)} compatible categories")
                    
                    # Look for shower bases and bathtubs in the results
                    for category in compatible_products:
                        category_name = category.get('category')
                        products = category.get('products', [])
                        
                        if category_name in ['Shower Bases', 'Bathtubs']:
                            print(f"\nFound {len(products)} compatible {category_name}:")
                            
                            for i, product in enumerate(products[:5], 1):  # Show only first 5 for brevity
                                print(f"  {i}. {product.get('sku')} - {product.get('name')}")
                                print(f"     Max Door Width: {product.get('max_door_width')}")
                                
                            if len(products) > 5:
                                print(f"     ... and {len(products) - 5} more")
                else:
                    print(f"❌ Door search failed: {data.get('message', 'Unknown error')}")
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                print(f"Raw response: {response.text[:200]}...")
        else:
            print(f"❌ API search failed: Status {response.status_code}")
            print(f"Response: {response.text[:100]}...")
    
    except Exception as e:
        print(f"Error in test: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    # Test with a shower door and a tub door
    shower_door_sku = "105410"  # Known shower door
    tub_door_sku = "137666"     # Known tub door
    
    print("\n===== TESTING SHOWER DOOR =====")
    test_door_compatibility(shower_door_sku)
    
    print("\n===== TESTING TUB DOOR =====")
    test_door_compatibility(tub_door_sku)