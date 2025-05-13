"""
Test script to check compatibility lookup
"""

import logging
import json
from logic import compatibility, bathtub_compatibility

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_compatibility(sku):
    """Test finding compatible products for a SKU"""
    print(f"\n===== Testing compatibility for SKU: {sku} =====")
    
    # Get data from compatibility module
    data = compatibility.load_data()
    
    # Get product details
    product_info = compatibility.get_product_details(data, sku)
    
    if product_info:
        print(f"Found product: {product_info.get('Product Name', 'Unknown')} in category: {product_info.get('category', 'Unknown')}")
        
        # Check if it's a bathtub SKU
        if product_info.get('category') == 'Bathtubs':
            print("Using bathtub compatibility logic")
            compatibles = bathtub_compatibility.find_bathtub_compatibilities(data, product_info)
            print(f"Found {len(compatibles)} compatible categories")
            # Show first few compatible products for each category
            for category in compatibles:
                cat_name = category.get('category', 'Unknown')
                products = category.get('products', [])
                print(f"  {cat_name}: {len(products)} products")
                # Show first 2 products as examples
                for i, product in enumerate(products[:2]):
                    print(f"    {i+1}. {product.get('sku', '')}: {product.get('Product Name', 'Unknown')}")
                    # Check if image URL exists
                    if 'Image URL' in product:
                        print(f"       Image URL: {product['Image URL']}")
                    else:
                        print("       No Image URL")
        else:
            print("Using standard compatibility logic")
            # Get compatible products 
            results = compatibility.find_compatible_products(sku)
            if results and 'compatibles' in results:
                compatibles = results['compatibles']
                print(f"Found {len(compatibles)} compatible categories")
                # Show first few compatible products for each category
                for category in compatibles:
                    cat_name = category.get('category', 'Unknown')
                    products = category.get('products', [])
                    print(f"  {cat_name}: {len(products)} products")
                    # Show first 2 products as examples
                    for i, product in enumerate(products[:2]):
                        print(f"    {i+1}. {product.get('sku', '')}: {product.get('name', 'Unknown')}")
                        # Check if image URL exists
                        if 'image_url' in product:
                            print(f"       Image URL: {product['image_url']}")
                        else:
                            print("       No Image URL")
    else:
        print(f"No product found for SKU: {sku}")

if __name__ == "__main__":
    # Test a shower base SKU
    test_compatibility("420006-L-502-001")
    
    # Test a bathtub SKU
    test_compatibility("105821")