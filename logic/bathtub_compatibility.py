"""
Bathtub compatibility module for the Compatibility Finder

This module provides functionality to find compatible products for bathtubs.
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
    """Check if brands and families match for bathtubs and walls"""
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

def find_bathtub_compatibilities(data, bathtub_info):
    """
    Find compatible products for a bathtub
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        bathtub_info (dict): Dictionary containing bathtub product information
        
    Returns:
        list: List of dictionaries containing category and compatible SKUs
    """
    compatibles = []
    tolerance = 3  # inches
    
    try:
        bathtub_width = bathtub_info.get("Max Door Width")
        bathtub_install = bathtub_info.get("Installation")
        bathtub_series = bathtub_info.get("Series")
        bathtub_brand = bathtub_info.get("Brand")
        bathtub_family = bathtub_info.get("Family")
        bathtub_nominal = bathtub_info.get("Nominal Dimensions")
        bathtub_length = bathtub_info.get("Length")
        bathtub_width_actual = bathtub_info.get("Width")
        
        # Check if the necessary data exists
        if not all([data.get('Tub Doors'), data.get('Walls')]):
            logger.warning("Missing required sheets for bathtub compatibility")
            return compatibles
            
        # ---------- Compatible Doors ----------
        compatible_doors = []
        compatible_door_skus = []
        
        if 'Tub Doors' in data:
            tub_doors_df = data['Tub Doors']
            for _, door in tub_doors_df.iterrows():
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_series = door.get("Series")
                door_id = str(door.get("Unique ID", "")).strip()

                if not door_id:
                    continue

                # Safe comparison with pandas scalars
                is_alcove = bathtub_install == "Alcove"
                width_valid = False
                if pd.notna(bathtub_width) and pd.notna(door_min_width) and pd.notna(door_max_width):
                    try:
                        width_valid = float(door_min_width) <= float(bathtub_width) <= float(door_max_width)
                    except (ValueError, TypeError):
                        width_valid = False
                
                series_valid = series_compatible(bathtub_series, door_series)
                
                if is_alcove and width_valid and series_valid:
                    # Add the SKU to the list
                    compatible_door_skus.append(door_id)
                    # Convert door row to dict for the result
                    door_dict = door.to_dict()
                    if door_dict and 'name' not in door_dict and 'Product Name' in door_dict:
                        door_dict['name'] = door_dict['Product Name']
                    compatible_doors.append(door_dict)
        
        if compatible_doors:
            compatibles.append({
                'category': 'Tub Doors',
                'products': compatible_doors,
                'skus': compatible_door_skus  # Add the list of compatible SKUs
            })
            
        # ---------- Compatible Walls ----------
        compatible_walls = []
        compatible_wall_skus = []
        
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

                if not wall_id:
                    continue

                # Safe comparison with pandas scalars
                is_tub_wall = "tub" in wall_type if wall_type else False
                series_valid = series_compatible(bathtub_series, wall_series)
                brand_family_valid = bathtub_brand_family_match(bathtub_brand, bathtub_family, wall_brand, wall_family)
                
                # Check nominal dimensions
                nominal_match = str(bathtub_nominal) == str(wall_nominal) if bathtub_nominal and wall_nominal else False
                
                # Check cut-to-size with tolerance
                cut_size_match = False
                if wall_cut == "Yes" and pd.notna(bathtub_length) and pd.notna(wall_length) and pd.notna(bathtub_width_actual) and pd.notna(wall_width):
                    try:
                        bl = float(bathtub_length)
                        wl = float(wall_length)
                        bw = float(bathtub_width_actual)
                        ww = float(wall_width)
                        t = float(tolerance)
                        
                        length_match = bl >= (wl - t) and bl <= (wl + t)
                        width_match = bw >= (ww - t) and bw <= (ww + t)
                        cut_size_match = length_match and width_match
                    except (ValueError, TypeError):
                        cut_size_match = False
                
                if is_tub_wall and series_valid and brand_family_valid and (nominal_match or cut_size_match):
                    # Add the SKU to the list
                    compatible_wall_skus.append(wall_id)
                    # Convert wall row to dict for the result
                    wall_dict = wall.to_dict()
                    if wall_dict and 'name' not in wall_dict and 'Product Name' in wall_dict:
                        wall_dict['name'] = wall_dict['Product Name']
                    compatible_walls.append(wall_dict)
        
        if compatible_walls:
            compatibles.append({
                'category': 'Walls',
                'products': compatible_walls,
                'skus': compatible_wall_skus  # Add the list of compatible SKUs
            })
                
    except Exception as e:
        logger.error(f"Error in find_bathtub_compatibilities: {str(e)}")
        
    return compatibles