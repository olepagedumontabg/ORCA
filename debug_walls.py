#!/usr/bin/env python3
"""
Debug script to check why walls aren't showing up for shower base 420000-500-001
"""

import pandas as pd
import sys
import os

# Add the project root to the path so we can import modules
sys.path.append('.')

from logic.compatibility import load_data, get_product_details

def debug_walls_issue():
    """Debug why walls aren't showing up for shower base 420000-500-001"""
    
    print("=== Debugging Walls Issue ===")
    
    # Load the data
    data = load_data()
    print(f"Loaded {len(data)} worksheets")
    
    # Get the shower base details
    base_sku = "420000-500-001"
    base_info = get_product_details(data, base_sku)
    
    if not base_info:
        print(f"❌ Could not find shower base {base_sku}")
        return
    
    print(f"✅ Found shower base: {base_info.get('Product Name')}")
    print(f"   Brand: {base_info.get('Brand')}")
    print(f"   Family: {base_info.get('Family')}")
    print(f"   Installation: {base_info.get('Installation')}")
    print(f"   Nominal Dimensions: {base_info.get('Nominal Dimensions')}")
    
    # Check for incompatibility reasons
    walls_cant_fit = base_info.get("Reason Walls Can't Fit")
    print(f"   Reason Walls Can't Fit: {walls_cant_fit}")
    
    if pd.notna(walls_cant_fit) and walls_cant_fit:
        print(f"❌ Walls blocked by incompatibility reason: {walls_cant_fit}")
        return
    else:
        print("✅ No walls incompatibility reason found")
    
    # Check if walls data exists
    if 'Walls' not in data:
        print("❌ No 'Walls' worksheet found in data")
        return
    
    walls_df = data['Walls']
    print(f"✅ Found {len(walls_df)} walls in data")
    
    # Show first few walls for reference
    print("\n=== Sample Walls ===")
    for i, (_, wall) in enumerate(walls_df.head(3).iterrows()):
        print(f"Wall {i+1}: {wall.get('Unique ID')} - {wall.get('Product Name')}")
        print(f"   Type: {wall.get('Type')}")
        print(f"   Brand: {wall.get('Brand')}")
        print(f"   Family: {wall.get('Family')}")
        print(f"   Series: {wall.get('Series')}")
        print(f"   Nominal Dimensions: {wall.get('Nominal Dimensions')}")
        print()

if __name__ == "__main__":
    debug_walls_issue()