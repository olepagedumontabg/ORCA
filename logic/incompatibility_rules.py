"""
Incompatibility Rules Module

This module maintains hard-coded product incompatibility rules that override
the data-driven compatibility logic. It provides functions to check if two products
should be considered incompatible regardless of what the data suggests, as well as
filter functions that can be applied to compatibility results.

Usage:
    from logic.incompatibility_rules import is_incompatible, filter_incompatible_products
    
    # Check individual compatibility
    if is_incompatible(product_a_sku, product_b_sku):
        # Skip this match
        
    # Or filter an entire list of compatible products
    compatible_products = filter_incompatible_products(source_sku, compatible_products_list)
"""

import logging

logger = logging.getLogger(__name__)

# Define two-way incompatibility pairs
# Each entry is a tuple of SKUs that are incompatible with each other
INCOMPATIBLE_PAIRS = [
    # Example: Bathtub 105821 is not compatible with Wall 139398
    ('105821', '139398'),
    # Add more incompatible pairs as needed
    
    # Test incompatibility - not real data, just for demonstration
    ('105821', '107181'),
]

# For one-way incompatibilities (A can't use B, but B can use A)
# This is a dict where key = source SKU, value = list of incompatible target SKUs
ONE_WAY_INCOMPATIBILITIES = {
    # '123456': ['789012', '345678'],  # Product 123456 cannot use products 789012 or 345678
}

def is_incompatible(source_sku, target_sku):
    """
    Check if two products are incompatible based on hard-coded rules
    
    Args:
        source_sku (str): SKU of the source product
        target_sku (str): SKU of the target product to check compatibility with
        
    Returns:
        bool: True if products are incompatible, False otherwise
    """
    # Ensure both SKUs are strings and non-empty
    if not source_sku or not target_sku:
        logger.debug(f"Empty SKU in incompatibility check: source={source_sku}, target={target_sku}")
        return False
    
    # Ensure SKUs are strings
    source_sku = str(source_sku).strip()
    target_sku = str(target_sku).strip()
    
    logger.debug(f"Checking incompatibility between {source_sku} and {target_sku}")
    logger.debug(f"Incompatible pairs: {INCOMPATIBLE_PAIRS}")
    
    # Check two-way incompatibilities (order doesn't matter)
    check1 = (source_sku, target_sku) in INCOMPATIBLE_PAIRS
    check2 = (target_sku, source_sku) in INCOMPATIBLE_PAIRS
    
    if check1 or check2:
        logger.info(f"Found incompatibility between {source_sku} and {target_sku}")
        return True
    
    # Check one-way incompatibilities (order matters)
    if source_sku in ONE_WAY_INCOMPATIBILITIES and target_sku in ONE_WAY_INCOMPATIBILITIES[source_sku]:
        logger.info(f"Found one-way incompatibility: {source_sku} cannot use {target_sku}")
        return True
    
    logger.debug(f"No incompatibility found between {source_sku} and {target_sku}")
    return False
    
def filter_incompatible_products(source_sku, compatible_products):
    """
    Filter a list of compatible products to remove any that are incompatible
    based on hard-coded rules.
    
    Args:
        source_sku (str): SKU of the source product
        compatible_products (list): List of dictionaries containing compatible products
        
    Returns:
        list: Filtered list with incompatible products removed
    """
    if not source_sku or not compatible_products:
        return compatible_products
        
    source_sku = str(source_sku).strip()
    filtered_products = []
    
    for product in compatible_products:
        target_sku = product.get("sku", "")
        if not target_sku:
            # If no SKU, keep the product (might be an error message or category)
            filtered_products.append(product)
            continue
            
        # Check if product is incompatible
        if is_incompatible(source_sku, target_sku):
            logger.info(f"Removing incompatible product {target_sku} from results for {source_sku}")
            continue
            
        # If not incompatible, keep it
        filtered_products.append(product)
        
    return filtered_products