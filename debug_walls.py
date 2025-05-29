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

    # Test wall matching logic specifically
    print("=== Testing Wall Matching Logic ===")
    print(f"Base installation: '{base_info.get('Installation')}'")
    print(f"Base series: '{base_info.get('Series')}'")
    print(f"Base brand: '{base_info.get('Brand')}'")
    print(f"Base family: '{base_info.get('Family')}'")
    print(f"Base nominal: '{base_info.get('Nominal Dimensions')}'")
    
    # Import the helper functions
    from logic.base_compatibility import series_compatible, brand_family_match
    
    # Test a few walls that should match
    base_install = str(base_info.get("Installation", "")).lower()
    base_series = base_info.get("Series")
    base_brand = base_info.get("Brand")
    base_family = base_info.get("Family")
    base_nominal = base_info.get("Nominal Dimensions")
    
    matching_count = 0
    
    print(f"\n--- Checking Wall Matches ---")
    for i, (_, wall) in enumerate(walls_df.iterrows()):
        if i >= 10:  # Only check first 10 for brevity
            break
            
        wall_type = str(wall.get("Type", "")).lower()
        wall_brand = wall.get("Brand")
        wall_series = wall.get("Series")
        wall_family = wall.get("Family")
        wall_nominal = wall.get("Nominal Dimensions")
        wall_id = str(wall.get("Unique ID", "")).strip()
        wall_name = wall.get("Product Name", "")
        
        print(f"\nWall {i+1}: {wall_id} - {wall_name}")
        print(f"   Type: '{wall_type}' (original: '{wall.get('Type', '')}')")
        
        # Check type matching
        alcove_type_match = "alcove shower" in wall_type
        corner_type_match = "corner shower" in wall_type
        print(f"   Type matches: alcove={'alcove shower' in wall_type}, corner={'corner shower' in wall_type}")
        
        # Check installation matching
        alcove_install_match = base_install in ["alcove", "alcove or corner"]
        corner_install_match = base_install in ["corner", "alcove or corner"]
        print(f"   Install matches: alcove={alcove_install_match}, corner={corner_install_match}")
        
        # Check series compatibility
        series_match = series_compatible(base_series, wall_series)
        print(f"   Series compatible: {series_match} (base: {base_series}, wall: {wall_series})")
        
        # Check brand/family match
        brand_match = brand_family_match(base_brand, base_family, wall_brand, wall_family)
        print(f"   Brand/family match: {brand_match}")
        
        # Overall matches
        alcove_match = (alcove_type_match and alcove_install_match and series_match and brand_match)
        corner_match = (corner_type_match and corner_install_match and series_match and brand_match)
        
        print(f"   FINAL: alcove_match={alcove_match}, corner_match={corner_match}")
        
        if alcove_match or corner_match:
            matching_count += 1
            print(f"   ✅ WALL MATCHES!")
            
            # Check nominal dimensions
            nominal_match = base_nominal == wall_nominal
            print(f"   Nominal match: {nominal_match} (base: '{base_nominal}', wall: '{wall_nominal}')")
    
    print(f"\n=== Summary ===")
    print(f"Total walls checked: {min(10, len(walls_df))}")
    print(f"Matching walls found: {matching_count}")

if __name__ == "__main__":
    debug_walls_issue()