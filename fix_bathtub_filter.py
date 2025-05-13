"""
Script to fix bathtub compatibility issues and normalize data formats
"""

import json
import os
import sys
import pandas as pd
import traceback

# Add the current directory to sys.path
sys.path.append('.')

try:
    from logic import compatibility, bathtub_compatibility
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

def update_door_products():
    """
    Update door products to include correct fields for filtering 
    """
    try:
        # Load data
        data = compatibility.load_data()
        
        # Check if Tub Doors exists
        if 'Tub Doors' not in data:
            print("No Tub Doors sheet found in data")
            return False
            
        # Update door products with missing fields
        doors_df = data['Tub Doors']
        
        # Make a copy of the dataframe to modify
        updated_df = doors_df.copy()
        
        # Add lowercase keys for consistency (door_type, glass_thickness)
        glass_count = 0
        door_type_count = 0
        
        for idx, row in updated_df.iterrows():
            # Check for Glass Thickness field
            if 'Glass Thickness' in row and pd.notna(row['Glass Thickness']):
                # Add glass_thickness field for JavaScript filtering
                updated_df.at[idx, 'glass_thickness'] = row['Glass Thickness']
                glass_count += 1
                
            # Check for Door Type field
            if 'Door Type' in row and pd.notna(row['Door Type']):
                # Add door_type field for JavaScript filtering
                updated_df.at[idx, 'door_type'] = row['Door Type']
                door_type_count += 1
        
        print(f"Added glass_thickness to {glass_count} products")
        print(f"Added door_type to {door_type_count} products")
        
        # Save the updated dataframe back to the data directory
        output_path = os.path.join('data', 'tub_doors_updated.xlsx')
        updated_df.to_excel(output_path, index=False)
        print(f"Updated Tub Doors saved to {output_path}")
        
        return True
    except Exception as e:
        print(f"Error updating door products: {str(e)}")
        traceback.print_exc()
        return False

def test_bathtub_compatibility():
    """
    Test bathtub compatibility
    """
    try:
        # Test bathtub SKU
        sku = "105821"
        print(f"\n===== Testing bathtub compatibility for SKU: {sku} =====")
        
        # Get data
        data = compatibility.load_data()
        
        # Get product details
        product_info = compatibility.get_product_details(data, sku)
        
        if not product_info:
            print(f"No product found for SKU: {sku}")
            return False
            
        print(f"Found product: {product_info.get('Product Name', 'Unknown')} in category: {product_info.get('category', 'Unknown')}")
        
        # Get compatible products using bathtub compatibility logic
        compatibles = bathtub_compatibility.find_bathtub_compatibilities(data, product_info)
        
        print(f"Found {len(compatibles)} compatible categories")
        
        # For each category, check the first few products
        for category in compatibles:
            cat_name = category.get('category', 'Unknown')
            products = category.get('products', [])
            print(f"  {cat_name}: {len(products)} products")
            
            # Count products with glass thickness/door type
            glass_count = sum(1 for p in products if 'glass_thickness' in p)
            door_type_count = sum(1 for p in products if 'door_type' in p)
            image_count = sum(1 for p in products if 'Image URL' in p)
            
            print(f"  - Products with glass_thickness: {glass_count}/{len(products)}")
            print(f"  - Products with door_type: {door_type_count}/{len(products)}")
            print(f"  - Products with Image URL: {image_count}/{len(products)}")
            
            # Show first 2 products as examples
            for i, product in enumerate(products[:2]):
                print(f"    {i+1}. {product.get('sku', '')}: {product.get('Product Name', 'Unknown')}")
                # Check for filtering fields
                print(f"       glass_thickness: {product.get('glass_thickness', 'None')}")
                print(f"       door_type: {product.get('door_type', 'None')}")
                # Check for image URL
                if 'Image URL' in product:
                    print(f"       Image URL: {product['Image URL']}")
                else:
                    print("       No Image URL")
        
        return True
    except Exception as e:
        print(f"Error testing bathtub compatibility: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Update door products
    print("Updating door products...")
    update_door_products()
    
    # Test bathtub compatibility
    print("\nTesting bathtub compatibility...")
    test_bathtub_compatibility()