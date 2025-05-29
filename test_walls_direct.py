#!/usr/bin/env python3
"""
Direct test of base compatibility function to see if walls are being returned
"""

import sys
sys.path.append('.')

from logic.compatibility import load_data, get_product_details
from logic.base_compatibility import find_base_compatibilities

def test_walls_direct():
    """Test the base compatibility function directly"""
    
    print("=== Direct Base Compatibility Test ===")
    
    # Load the data
    data = load_data()
    
    # Get the shower base details
    base_sku = "420000-500-001"
    base_info = get_product_details(data, base_sku)
    
    if not base_info:
        print(f"❌ Could not find shower base {base_sku}")
        return
    
    print(f"✅ Found shower base: {base_info.get('Product Name')}")
    
    # Test the compatibility function directly
    print("\n=== Calling find_base_compatibilities directly ===")
    compatible_results = find_base_compatibilities(data, base_info)
    
    print(f"Number of compatibility results: {len(compatible_results)}")
    
    for i, result in enumerate(compatible_results):
        category = result.get('category', 'Unknown')
        if 'products' in result:
            products = result['products']
            print(f"{i+1}. Category: {category} - {len(products)} products")
            if category == 'Walls':
                print("   WALLS FOUND!")
                for j, wall in enumerate(products[:3]):  # Show first 3
                    print(f"     Wall {j+1}: {wall.get('sku')} - {wall.get('name')}")
        elif 'reason' in result:
            print(f"{i+1}. Category: {category} - Incompatible: {result['reason']}")

if __name__ == "__main__":
    test_walls_direct()