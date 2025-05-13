"""
Test script to specifically check Duel vs Duel Alto ranking order
"""
import logging
import sys
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("duel_test")

def test_duel_order(sku="420043-541-001"):
    """Test specifically for Duel vs Duel Alto ranking order"""
    logger.info(f"Testing Duel/Duel Alto order for SKU: {sku}")
    
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
        
        # Find all Duel products across all categories
        duel_products = []
        duel_alto_products = []
        
        for category_info in compatibles:
            category = category_info.get("category")
            products = category_info.get("products", [])
            
            for product in products:
                name = product.get("name", "")
                if not name and product.get("is_combo"):
                    main_product = product.get("main_product", {})
                    name = main_product.get("name", "")
                
                if name and "Duel Alto" in name:
                    duel_alto_products.append({
                        "category": category,
                        "position": len(duel_alto_products) + 1,
                        "product": product
                    })
                elif name and "Duel" in name:
                    duel_products.append({
                        "category": category,
                        "position": len(duel_products) + 1,
                        "product": product
                    })
        
        # Print Duel Alto products
        if duel_alto_products:
            logger.info(f"Found {len(duel_alto_products)} Duel Alto products:")
            for item in duel_alto_products:
                product = item["product"]
                name = product.get("name", "")
                if not name and product.get("is_combo"):
                    main_product = product.get("main_product", {})
                    name = main_product.get("name", "")
                    sku = main_product.get("sku", "")
                else:
                    sku = product.get("sku", "")
                    
                logger.info(f"  Category: {item['category']}, Position: {item['position']}, SKU: {sku}, Name: {name}")
        else:
            logger.info("No Duel Alto products found")
            
        # Print regular Duel products
        if duel_products:
            logger.info(f"Found {len(duel_products)} regular Duel products:")
            for item in duel_products:
                product = item["product"]
                name = product.get("name", "")
                if not name and product.get("is_combo"):
                    main_product = product.get("main_product", {})
                    name = main_product.get("name", "")
                    sku = main_product.get("sku", "")
                else:
                    sku = product.get("sku", "")
                    
                logger.info(f"  Category: {item['category']}, Position: {item['position']}, SKU: {sku}, Name: {name}")
        else:
            logger.info("No regular Duel products found")
            
        # Check if Duel Alto products appear before regular Duel products
        if duel_alto_products and duel_products:
            # Get the positions of Duel products in the overall sorted list
            min_alto_position = min([p.get("product", {}).get("_position", 999) for p in duel_alto_products], default=999)
            min_duel_position = min([p.get("product", {}).get("_position", 999) for p in duel_products], default=999)
            
            if min_alto_position < min_duel_position:
                logger.info("✓ SUCCESS: Duel Alto products appear before regular Duel products")
            else:
                logger.error("✗ FAILED: Duel Alto products do not appear before regular Duel products")
                
    except Exception as e:
        logger.error(f"Error in test_duel_order: {str(e)}")

if __name__ == "__main__":
    # Use command line argument if provided, otherwise use default
    sku = sys.argv[1] if len(sys.argv) > 1 else "420043-541-001"
    test_duel_order(sku)