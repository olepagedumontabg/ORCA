"""
Test script to check if products are correctly sorted by Ranking value
"""
import logging
import sys
from logic import compatibility
import pandas as pd

# Configure logging to show detailed information
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.StreamHandler(sys.stdout)
                   ])
logger = logging.getLogger("ranking_test")

def test_ranking_order(sku="137030"):
    """Test ranking order for a base product search"""
    logger.info(f"Testing ranking order for SKU: {sku}")
    
    # Call the compatibility function
    result = compatibility.find_compatible_products(sku)
    
    if not result or not result.get('product'):
        logger.error(f"No product found for SKU: {sku}")
        return
    
    product = result['product']
    logger.info(f"Found product: {product.get('name')} ({product.get('category')})")
    
    # Check if we have compatible products
    compatibles = result.get('compatibles', [])
    if not compatibles:
        logger.info("No compatible products found")
        return
    
    logger.info(f"Found {len(compatibles)} compatible categories")
    
    # Loop through each category and check ranking order
    for category_info in compatibles:
        category = category_info.get('category')
        products = category_info.get('products', [])
        
        if not products:
            logger.info(f"Category {category}: No products")
            continue
            
        logger.info(f"Category {category}: {len(products)} products")
        
        # Check if products are sorted by ranking
        prev_ranking = -1
        all_sorted = True
        
        for i, product in enumerate(products):
            ranking = product.get('_ranking', 999)
            product_name = product.get('name', 'Unknown')
            sku = product.get('sku', 'Unknown')
            if product.get('is_combo'):
                sku = product.get('main_product', {}).get('sku', 'Unknown')
                product_name = product.get('main_product', {}).get('name', 'Unknown')
                
            logger.info(f"  [{i+1}] {sku} - {product_name} - Ranking: {ranking}")
            
            # Check if this product's ranking is >= the previous one
            if prev_ranking != -1 and ranking < prev_ranking:
                logger.warning(f"  Ranking order incorrect: {ranking} should not be before {prev_ranking}")
                all_sorted = False
                
            prev_ranking = ranking
                
        if all_sorted:
            logger.info(f"✓ Category {category}: Products are correctly sorted by Ranking")
        else:
            logger.error(f"✗ Category {category}: Products are NOT correctly sorted by Ranking")

if __name__ == "__main__":
    # Use a shower base SKU to test
    sku = "137030"  # Default test SKU (a shower base)
    
    # Check if user provided a different SKU
    if len(sys.argv) > 1:
        sku = sys.argv[1]
        
    test_ranking_order(sku)