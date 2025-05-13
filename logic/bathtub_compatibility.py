"""
Bathtub Compatibility Module

This module provides functions to determine compatibility between bathtubs and other products
such as tub doors and walls. It enhances the product compatibility finder with additional
relationships specific to bathtubs.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Constants
TOLERANCE_INCHES = 3  # 3 inches tolerance for dimension matching


def series_compatible(base_series, compare_series):
    """
    Check if two series are compatible based on business rules.
    
    Args:
        base_series (str): Series of the base product
        compare_series (str): Series of the product to compare with
        
    Returns:
        bool: True if the series are compatible, False otherwise
    """
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False


def bathtub_brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """
    Check if bathtub brand/family matches wall brand/family based on specific business rules.
    
    Args:
        base_brand (str): Brand of the bathtub
        base_family (str): Family of the bathtub
        wall_brand (str): Brand of the wall
        wall_family (str): Family of the wall
        
    Returns:
        bool: True if there's a match according to the business rules, False otherwise
    """
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
        list: List of dictionaries containing category and compatible products
    """
    results = []
    
    # Check if necessary data exists
    if 'Tub Doors' not in data or 'Walls' not in data:
        logger.warning("Missing required sheets for bathtub compatibility")
        return results
    
    tub_doors_df = data['Tub Doors']
    walls_df = data['Walls']
    
    # Get bathtub properties
    tub_width = bathtub_info.get("Max Door Width")
    tub_install = bathtub_info.get("Installation")
    tub_series = bathtub_info.get("Series")
    tub_brand = bathtub_info.get("Brand")
    tub_family = bathtub_info.get("Family")
    tub_nominal = bathtub_info.get("Nominal Dimensions")
    tub_length = bathtub_info.get("Length")
    tub_width_actual = bathtub_info.get("Width")
    
    # Find compatible tub doors
    compatible_doors = []
    for _, door in tub_doors_df.iterrows():
        try:
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_series = door.get("Series")
            door_id = str(door.get("Unique ID", "")).strip()
            
            if not door_id:
                continue
                
            if (
                tub_install == "Alcove" and
                pd.notna(tub_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                door_min_width <= tub_width <= door_max_width and
                series_compatible(tub_series, door_series)
            ):
                # Format door product data for the frontend
                door_data = door.to_dict()
                # Remove any NaN values
                door_data = {k: v for k, v in door_data.items() if pd.notna(v)}
                
                # Create a properly formatted product entry for the frontend
                product_dict = {
                    "sku": door_id,
                    "is_combo": False,
                    "_ranking": door_data.get("Ranking", 999),
                    "name": door_data.get("Product Name", ""),
                    "image_url": "",  # We'll rely on image_handler elsewhere
                    "nominal_dimensions": "",
                    "brand": door_data.get("Brand", ""),
                    "series": door_data.get("Series", ""),
                    "glass_thickness": door_data.get("Glass Thickness", ""),
                    "door_type": door_data.get("Door Type", "")
                }
                compatible_doors.append(product_dict)
        except Exception as e:
            logger.error(f"Error processing tub door: {e}")
    
    # Find compatible walls
    compatible_walls = []
    for _, wall in walls_df.iterrows():
        try:
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
                
            if (
                "tub" in wall_type and
                series_compatible(tub_series, wall_series) and
                bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                (
                    tub_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     pd.notna(tub_length) and pd.notna(wall_length) and
                     pd.notna(tub_width_actual) and pd.notna(wall_width) and
                     tub_length >= wall_length - TOLERANCE_INCHES and
                     tub_length <= wall_length + TOLERANCE_INCHES and
                     tub_width_actual >= wall_width - TOLERANCE_INCHES and
                     tub_width_actual <= wall_width + TOLERANCE_INCHES)
                )
            ):
                # Format wall product data for the frontend
                wall_data = wall.to_dict()
                # Remove any NaN values
                wall_data = {k: v for k, v in wall_data.items() if pd.notna(v)}
                compatible_walls.append(wall_data)
        except Exception as e:
            logger.error(f"Error processing wall: {e}")
    
    # Add results to the output
    if compatible_doors:
        results.append({"category": "Tub Doors", "products": compatible_doors})
    
    if compatible_walls:
        results.append({"category": "Walls", "products": compatible_walls})
    
    return results