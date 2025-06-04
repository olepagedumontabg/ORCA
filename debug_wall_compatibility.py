#!/usr/bin/env python3
"""
Debug script to identify why walls aren't showing up in compatibility results
"""

import sys
import os
sys.path.insert(0, '.')

from logic.compatibility import load_data, get_product_details
from logic.base_compatibility import find_base_compatibilities

def debug_wall_compatibility():
    """Debug wall compatibility for SW001013"""
    
    # Load data
    data = load_data()
    
    # Get Swan base product details
    base_sku = "SW001013"
    base_info = get_product_details(data, base_sku)
    
    if not base_info:
        print(f"Base product {base_sku} not found")
        return
    
    print(f"Base product: {base_info}")
    print(f"Base brand: {base_info.get('Brand')}")
    print(f"Base series: {base_info.get('Series')}")
    print(f"Base family: {base_info.get('Family')}")
    print(f"Base installation: {base_info.get('Installation')}")
    print()
    
    # Get compatibility results
    results = find_base_compatibilities(data, base_info)
    
    # Find walls in results
    wall_results = [r for r in results if r.get('category') == 'Walls']
    
    print(f"Wall results found: {len(wall_results)}")
    for result in wall_results:
        if 'products' in result:
            print(f"  Walls category: {len(result['products'])} products")
            for product in result['products'][:5]:  # Show first 5
                print(f"    - {product.get('sku')}: {product.get('name')}")
        elif 'reason' in result:
            print(f"  Walls incompatibility reason: {result['reason']}")
    
    # Check if walls exist in data
    if 'Walls' in data:
        walls_df = data['Walls']
        swan_walls = walls_df[walls_df['Brand'].str.lower() == 'swan']
        print(f"\nTotal Swan walls in data: {len(swan_walls)}")
        
        if len(swan_walls) > 0:
            print("Sample Swan walls:")
            for _, wall in swan_walls.head().iterrows():
                print(f"  - {wall.get('Unique ID')}: {wall.get('Product Name')} (Type: {wall.get('Type')})")

if __name__ == "__main__":
    debug_wall_compatibility()