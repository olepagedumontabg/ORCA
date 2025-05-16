"""
SKU Exclusions Module

This module provides functionality to exclude specific SKU pairs from being shown
as compatible matches, regardless of what the compatibility algorithms determine.
"""

# Global set to store excluded SKU pairs
# Each pair is stored as a frozenset of two SKUs, which is hashable and order-independent
# This allows us to check for exclusions regardless of which SKU is the source or target
EXCLUDED_PAIRS = set()

def add_exclusion(sku1, sku2):
    """
    Add a pair of SKUs to the exclusion list.
    
    Args:
        sku1 (str): First SKU
        sku2 (str): Second SKU
    """
    EXCLUDED_PAIRS.add(frozenset([sku1, sku2]))
    
def remove_exclusion(sku1, sku2):
    """
    Remove a pair of SKUs from the exclusion list.
    
    Args:
        sku1 (str): First SKU
        sku2 (str): Second SKU
    """
    pair = frozenset([sku1, sku2])
    if pair in EXCLUDED_PAIRS:
        EXCLUDED_PAIRS.remove(pair)
        
def is_excluded(sku1, sku2):
    """
    Check if a pair of SKUs is excluded from compatibility.
    
    Args:
        sku1 (str): First SKU
        sku2 (str): Second SKU
        
    Returns:
        bool: True if the pair is excluded, False otherwise
    """
    return frozenset([sku1, sku2]) in EXCLUDED_PAIRS

def load_exclusions_from_list(exclusion_list):
    """
    Load multiple exclusions from a list of SKU pairs.
    
    Args:
        exclusion_list (list): List of tuples, each containing two SKUs
    """
    for sku1, sku2 in exclusion_list:
        add_exclusion(sku1, sku2)

# Initialize with some example exclusions
# These can be modified or loaded from a file/database as needed
INITIAL_EXCLUSIONS = [
    # Example format: ('SKU1', 'SKU2')
    # ('105409', '107180'),  # Uncomment and add real SKUs as needed
]

# Load initial exclusions
load_exclusions_from_list(INITIAL_EXCLUSIONS)