"""
Test script to validate search results with ranking order
"""
import logging
import sys
import requests
import json
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("search_test")

def test_search(sku="420043-541-001"):
    """Test search functionality with ranking order"""
    logger.info(f"Testing search for SKU: {sku}")
    
    try:
        # Make a search request to the local server
        response = requests.post(
            "http://localhost:5000/search",
            data={"sku": sku}
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Failed to search: {response.status_code} - {response.text}")
            return
        
        # Parse the response
        try:
            result = response.json()
        except Exception as e:
            logger.error(f"Failed to parse response: {str(e)}")
            return
        
        # Check if the search was successful
        if not result.get("success", False):
            logger.error(f"Search failed: {result.get('message', 'Unknown error')}")
            return
        
        # Print the product info
        product = result.get("product", {})
        logger.info(f"Found product: {product.get('name')} ({product.get('category')})")
        
        # Check if we have compatible products
        compatibles = result.get("compatibles", [])
        if not compatibles:
            logger.info("No compatible products found")
            return
        
        logger.info(f"Found {len(compatibles)} compatible categories")
        
        # Loop through each category and print products
        for category_info in compatibles:
            category = category_info.get("category")
            products = category_info.get("products", [])
            
            if not products:
                logger.info(f"Category {category}: No products")
                continue
                
            logger.info(f"Category {category}: {len(products)} products")
            
            # Print each product
            for i, product in enumerate(products):
                is_combo = product.get("is_combo", False)
                
                if is_combo:
                    main_product = product.get("main_product", {})
                    sku = main_product.get("sku", "Unknown")
                    name = main_product.get("name", "Unknown")
                    brand = main_product.get("brand", "")
                    series = main_product.get("series", "")
                    door_type = main_product.get("door_type", "")
                    
                    sec_product = product.get("secondary_product", {})
                    sec_sku = sec_product.get("sku", "Unknown")
                    sec_name = sec_product.get("name", "Unknown")
                    
                    logger.info(f"  [{i+1}] COMBO: {sku} + {sec_sku}")
                    logger.info(f"      Main: {name}")
                    logger.info(f"      Secondary: {sec_name}")
                    logger.info(f"      Brand: {brand}, Series: {series}, Door Type: {door_type}")
                else:
                    sku = product.get("sku", "Unknown")
                    name = product.get("name", "Unknown")
                    brand = product.get("brand", "")
                    series = product.get("series", "")
                    door_type = product.get("door_type", "")
                    
                    logger.info(f"  [{i+1}] {sku} - {name}")
                    logger.info(f"      Brand: {brand}, Series: {series}, Door Type: {door_type}")
                
                # Add a blank line for readability
                if i < len(products) - 1:
                    logger.info("")
                    
    except Exception as e:
        logger.error(f"Error in test_search: {str(e)}")

if __name__ == "__main__":
    # Use command line argument if provided, otherwise use default
    sku = sys.argv[1] if len(sys.argv) > 1 else "420043-541-001"
    test_search(sku)