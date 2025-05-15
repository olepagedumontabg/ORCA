#!/usr/bin/env python
"""
Test script for wall backward compatibility search.
This script tests the ability to find compatible shower bases and bathtubs for a given wall.
"""

import requests
import json
import sys

def test_wall_compatibility(wall_sku):
    """
    Test the backward compatibility search for a wall.
    Finds which shower bases or bathtubs are compatible with the specified wall.
    """
    print(f"Testing backward compatibility for wall SKU: {wall_sku}")
    
    try:
        # Call the search API
        response = requests.post('http://localhost:5000/search', data={'sku': wall_sku})
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if data.get('success', False):
                    print("\n✅ Wall found successfully")
                    
                    # Print wall details
                    wall_info = data.get('product', {})
                    print(f"\nWall Details:")
                    print(f"  SKU: {wall_info.get('sku')}")
                    print(f"  Name: {wall_info.get('name')}")
                    print(f"  Category: {wall_info.get('category')}")
                    print(f"  Type: {wall_info.get('type')}")
                    print(f"  Nominal Dimensions: {wall_info.get('nominal_dimensions')}")
                    
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
                                print(f"     Nominal Dimensions: {product.get('nominal_dimensions')}")
                                
                            if len(products) > 5:
                                print(f"     ... and {len(products) - 5} more")
                else:
                    print(f"❌ Wall search failed: {data.get('message', 'Unknown error')}")
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
    # Test with both a tub wall and a shower wall
    tub_wall_sku = "103418"  # Known tub wall (Utile 6032 Tub Wall Kit)
    shower_wall_sku = "107466"  # Known shower wall (Utile 6036 Shower Wall Kit)
    
    print("\n===== TESTING TUB WALL =====")
    test_wall_compatibility(tub_wall_sku)
    
    print("\n===== TESTING SHOWER WALL =====")
    test_wall_compatibility(shower_wall_sku)