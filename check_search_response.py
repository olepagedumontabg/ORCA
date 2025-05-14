#!/usr/bin/env python
import requests
import json

def check_search_response(sku):
    """
    Check the response from the search API for a specific SKU
    """
    print(f"Checking search response for SKU: {sku}")
    
    try:
        response = requests.post('http://localhost:5000/search', data={'sku': sku})
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                print(f"Search success: {data.get('success', False)}")
                
                # Check product details
                product = data.get('product', {})
                if product:
                    print("\nProduct Details:")
                    print(f"  SKU: {product.get('sku')}")
                    print(f"  Name: {product.get('name')}")
                    print(f"  Category: {product.get('category')}")
                    print(f"  Max Door Width: {product.get('max_door_width')}")
                    
                    # This is important - check if the category exactly matches "Bathtubs"
                    if product.get('category') == 'Bathtubs':
                        print("✅ Category correctly identified as 'Bathtubs'")
                    else:
                        print(f"❌ Category not identified as 'Bathtubs': {product.get('category')}")
                        
                else:
                    print("❌ No product details returned")
                
                # Check for compatibles
                compatibles = data.get('compatibles', [])
                print(f"\nCompatible products: {len(compatibles)} categories")
                
                return True
                
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                print(f"Raw response (first 200 chars): {response.text[:200]}...")
        else:
            print(f"❌ API search failed: Status {response.status_code}")
            print(f"Response: {response.text[:100]}...")
        
    except Exception as e:
        print(f"Error searching via API: {str(e)}")
        
    return False

if __name__ == "__main__":
    # Test a known bathtub SKU
    sku_to_check = "105821"  # Brome 6030
    
    # Check the bathtub search response
    check_search_response(sku_to_check)