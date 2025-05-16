"""
Incompatibility Rules Module

This module maintains hard-coded product incompatibility rules that override
the data-driven compatibility logic. It provides functions to check if two products
should be considered incompatible regardless of what the data suggests.

Usage:
    from logic.incompatibility_rules import is_incompatible
    if is_incompatible(product_a_sku, product_b_sku):
        # Skip this match
"""

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
    # Check two-way incompatibilities (order doesn't matter)
    if (source_sku, target_sku) in INCOMPATIBLE_PAIRS or (target_sku, source_sku) in INCOMPATIBLE_PAIRS:
        return True
        
    # Check one-way incompatibilities (order matters)
    if source_sku in ONE_WAY_INCOMPATIBILITIES and target_sku in ONE_WAY_INCOMPATIBILITIES[source_sku]:
        return True
        
    return False