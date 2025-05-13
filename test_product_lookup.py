"""
Test script to check product lookup
"""

import logging
from logic import compatibility

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_product(sku):
    """Test looking up a product by SKU"""
    print(f"\n===== Testing SKU: {sku} =====")
    
    # Get data from compatibility module
    data = compatibility.load_data()
    
    # Get product details
    product_info = compatibility.get_product_details(data, sku)
    
    if product_info:
        print(f"Found product: {product_info.get('Product Name', 'Unknown')} in category: {product_info.get('category', 'Unknown')}")
        print(f"Unique ID: {product_info.get('Unique ID', '')}")
        print(f"Brand: {product_info.get('Brand', '')}, Series: {product_info.get('Series', '')}")
        
        # Print image URL if available
        if 'Image URL' in product_info and product_info['Image URL']:
            print(f"Direct Image URL: {product_info['Image URL']}")
        else:
            print("No direct Image URL found")
            
        return product_info
    else:
        print(f"No product found for SKU: {sku}")
        return None

if __name__ == "__main__":
    # Test a shower base SKU
    test_product("420006-L-502-001")
    
    # Test a bathtub SKU
    test_product("105821")