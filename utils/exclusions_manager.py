"""
SKU Exclusions Manager

This utility allows you to manage exclusions between SKUs.
Excluded pairs will never be shown as compatible, overriding any compatibility logic.
"""

import os
import csv
import logging
from logic import exclusions

# Configure logging
logger = logging.getLogger(__name__)

# Path to exclusions CSV
EXCLUSIONS_FILE = 'data/exclusions.csv'

def load_exclusions():
    """
    Load exclusions from CSV file into the exclusions module.
    Creates an empty CSV file if it doesn't exist.
    
    Returns:
        int: Number of exclusion pairs loaded
    """
    if not os.path.exists(EXCLUSIONS_FILE):
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(EXCLUSIONS_FILE), exist_ok=True)
        
        # Create a new CSV file with headers
        with open(EXCLUSIONS_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['SKU1', 'SKU2', 'Reason'])
        logger.info(f"Created new exclusions file at {EXCLUSIONS_FILE}")
        return 0
    
    # Read existing exclusions
    exclusion_pairs = []
    try:
        with open(EXCLUSIONS_FILE, 'r', newline='') as file:
            reader = csv.reader(file)
            # Skip header
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    sku1, sku2 = row[0].strip(), row[1].strip()
                    exclusion_pairs.append((sku1, sku2))
        
        # Clear existing exclusions and load new ones
        exclusions.EXCLUDED_PAIRS.clear()
        exclusions.load_exclusions_from_list(exclusion_pairs)
        logger.info(f"Loaded {len(exclusion_pairs)} exclusion pairs from {EXCLUSIONS_FILE}")
        return len(exclusion_pairs)
    except Exception as e:
        logger.error(f"Error loading exclusions from CSV: {str(e)}")
        return 0

def add_exclusion(sku1, sku2, reason=""):
    """
    Add a new exclusion pair to the CSV file and memory.
    
    Args:
        sku1 (str): First SKU
        sku2 (str): Second SKU
        reason (str, optional): Reason for the exclusion
    """
    # Ensure SKUs are strings and properly formatted
    sku1, sku2 = str(sku1).strip(), str(sku2).strip()
    
    # Load current exclusions if not already loaded
    if not exclusions.EXCLUDED_PAIRS:
        load_exclusions()
    
    # Check if this pair already exists
    if exclusions.is_excluded(sku1, sku2):
        logger.info(f"Exclusion pair {sku1}-{sku2} already exists, not adding again")
        return False
    
    try:
        # Add to CSV file
        with open(EXCLUSIONS_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([sku1, sku2, reason])
        
        # Add to memory
        exclusions.add_exclusion(sku1, sku2)
        logger.info(f"Added exclusion pair: {sku1}-{sku2} with reason: {reason}")
        return True
    except Exception as e:
        logger.error(f"Error adding exclusion {sku1}-{sku2}: {str(e)}")
        return False

def remove_exclusion(sku1, sku2):
    """
    Remove an exclusion pair from the CSV file and memory.
    
    Args:
        sku1 (str): First SKU
        sku2 (str): Second SKU
    """
    # Ensure SKUs are strings and properly formatted
    sku1, sku2 = str(sku1).strip(), str(sku2).strip()
    
    # Check if this pair exists
    if not exclusions.is_excluded(sku1, sku2):
        logger.info(f"Exclusion pair {sku1}-{sku2} does not exist, nothing to remove")
        return False
    
    try:
        # Remove from memory first
        exclusions.remove_exclusion(sku1, sku2)
        
        # Read all exclusions from CSV
        rows = []
        with open(EXCLUSIONS_FILE, 'r', newline='') as file:
            reader = csv.reader(file)
            header = next(reader)  # Save header
            for row in reader:
                if len(row) >= 2:
                    csv_sku1, csv_sku2 = row[0].strip(), row[1].strip()
                    # Keep all rows except the one we want to remove
                    if not ((csv_sku1 == sku1 and csv_sku2 == sku2) or 
                            (csv_sku1 == sku2 and csv_sku2 == sku1)):
                        rows.append(row)
        
        # Write back all rows except the removed one
        with open(EXCLUSIONS_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)
        
        logger.info(f"Removed exclusion pair: {sku1}-{sku2}")
        return True
    except Exception as e:
        logger.error(f"Error removing exclusion {sku1}-{sku2}: {str(e)}")
        return False

def list_exclusions():
    """
    List all exclusion pairs.
    
    Returns:
        list: List of tuples containing (sku1, sku2, reason)
    """
    if not os.path.exists(EXCLUSIONS_FILE):
        load_exclusions()  # This will create the file
        return []
    
    exclusion_list = []
    try:
        with open(EXCLUSIONS_FILE, 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    sku1, sku2 = row[0].strip(), row[1].strip()
                    reason = row[2].strip() if len(row) > 2 else ""
                    exclusion_list.append((sku1, sku2, reason))
        return exclusion_list
    except Exception as e:
        logger.error(f"Error listing exclusions: {str(e)}")
        return []