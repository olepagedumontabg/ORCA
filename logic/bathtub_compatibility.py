"""
Bathtub compatibility logic for finding compatible products.
This module handles finding compatible doors and walls for bathtubs.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def bathtub_brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for bathtub-wall compatibility"""
    base_brand = str(base_brand).strip().lower()
    base_family = str(base_family).strip().lower()
    wall_brand = str(wall_brand).strip().lower()
    wall_family = str(wall_family).strip().lower()

    # Maax restriction
    if base_brand == "maax" and wall_brand != "maax":
        return False

    return (
        (base_brand == "swan" and wall_brand == "swan") or
        (base_brand == "bootz" and wall_brand == "bootz") or
        (base_family == "olio" and wall_family == "olio") or
        (base_family == "vellamo" and wall_brand == "vellamo") or
        (base_family in ["nomad", "mackenzie", "exhibit", "new town", "rubix", "bosca", "cocoon", "corinthia"] and
         wall_family in ["utile", "nextile", "versaline"])
    )

def find_bathtub_compatibilities(data, tub_info):
    """
    Find compatible products for a bathtub
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        tub_info (dict): Dictionary containing bathtub product information
        
    Returns:
        list: List of dictionaries containing category and compatible SKUs
    """
    compatible_categories = []
    tub_width = tub_info.get("Max Door Width")
    tub_install = tub_info.get("Installation")
    tub_series = tub_info.get("Series")
    tub_brand = tub_info.get("Brand")
    tub_family = tub_info.get("Family")
    tub_nominal = tub_info.get("Nominal Dimensions")
    tub_length = tub_info.get("Length")
    tub_width_actual = tub_info.get("Width")
    
    tolerance = 3  # inches
    
    # Find compatible doors
    door_matches = []
    if 'Tub Doors' in data and pd.notna(tub_width) and tub_install == "Alcove":
        tub_doors_df = data['Tub Doors']
        
        for _, door in tub_doors_df.iterrows():
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_series = door.get("Series")
            
            # Ensure we have a string ID - handle int/float values properly
            door_id = door.get("Unique ID", "")
            if pd.isna(door_id) or door_id == "":
                continue
                
            # Convert to string to ensure compatibility with the rest of the code
            door_id = str(door_id).strip()
                
            if (
                pd.notna(door_min_width) and pd.notna(door_max_width) and
                door_min_width <= tub_width <= door_max_width and
                series_compatible(tub_series, door_series)
            ):
                # Create a product dictionary with all available info
                door_product = {k: v for k, v in door.items() if pd.notna(v)}
                door_product['sku'] = door_id
                door_matches.append(door_product)
                
    if door_matches:
        compatible_categories.append({
            'category': 'Tub Doors',
            'products': door_matches
        })
    
    # Find compatible walls
    wall_matches = []
    if 'Walls' in data:
        walls_df = data['Walls']
        
        for _, wall in walls_df.iterrows():
            wall_type = str(wall.get("Type", "")).lower()
            wall_brand = wall.get("Brand")
            wall_series = wall.get("Series")
            wall_family = wall.get("Family")
            wall_nominal = wall.get("Nominal Dimensions")
            wall_length = wall.get("Length")
            wall_width = wall.get("Width")
            wall_cut = wall.get("Cut to Size")
            wall_id = str(wall.get("Unique ID", "")).strip()
            
            if not wall_id or "tub" not in wall_type:
                continue
                
            if (
                series_compatible(tub_series, wall_series) and
                bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                (
                    tub_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     pd.notna(tub_length) and pd.notna(wall_length) and
                     pd.notna(tub_width_actual) and pd.notna(wall_width) and
                     tub_length >= wall_length - tolerance and
                     tub_length <= wall_length + tolerance and
                     tub_width_actual >= wall_width - tolerance and
                     tub_width_actual <= wall_width + tolerance)
                )
            ):
                # Create a product dictionary with all available info
                wall_product = {k: v for k, v in wall.items() if pd.notna(v)}
                wall_product['sku'] = wall_id
                wall_matches.append(wall_product)
                
    if wall_matches:
        compatible_categories.append({
            'category': 'Walls',
            'products': wall_matches
        })
        
    return compatible_categories