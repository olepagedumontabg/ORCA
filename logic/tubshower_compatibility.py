"""
Tub Shower Compatibility Module

This module provides functions to determine compatibility between tub shower units and doors.
It enhances the product compatibility finder with additional relationships specific to tub shower units.
"""

import logging
import pandas as pd
from logic import image_handler

logger = logging.getLogger(__name__)

def series_compatible(base_series, compare_series):
    """
    Check if two series are compatible based on business rules.
    
    Args:
        base_series (str): Series of the base product
        compare_series (str): Series of the product to compare with
        
    Returns:
        bool: True if the series are compatible, False otherwise
    """
    base_series = str(base_series).strip() if base_series else ""
    compare_series = str(compare_series).strip() if compare_series else ""

    if not base_series or not compare_series:
        return False
    if base_series.lower() == compare_series.lower():
        return True
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def find_tubshower_compatibilities(data, tubshower_info):
    """
    Find compatible doors for a tub shower
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        tubshower_info (dict): Dictionary containing tub shower product information
        
    Returns:
        list: List of dictionaries containing category and compatible products
              or dictionaries with incompatibility reasons
    """
    results = []
    incompatibility_reasons = {}
    
    # Check for incompatibility reasons
    doors_cant_fit_reason = tubshower_info.get("Reason Doors Can't Fit")
    
    # If there are specific reasons why doors can't fit, add them to the incompatibility reasons
    if pd.notna(doors_cant_fit_reason) and doors_cant_fit_reason:
        incompatibility_reasons["Tub Doors"] = doors_cant_fit_reason
        logger.info(f"Tub doors incompatibility reason found: {doors_cant_fit_reason}")

    # Check if necessary data exists
    if 'Tub Doors' not in data:
        logger.warning("Missing Tub Doors sheet")
        
        # Still add incompatibility reasons even if missing sheets
        for category, reason in incompatibility_reasons.items():
            results.append({
                "category": category,
                "incompatible_reason": reason
            })
        return results

    tub_doors_df = data['Tub Doors']
    
    # Get tub shower properties
    tub_width = tubshower_info.get("Max Door Width")
    tub_height = tubshower_info.get("Max Door Height")
    tub_series = tubshower_info.get("Series")
    
    logger.debug(f"Finding doors for tub shower {tubshower_info.get('Unique ID')} - {tubshower_info.get('Product Name')}")
    logger.debug(f"Tub shower properties: Width={tub_width}, Height={tub_height}, Series={tub_series}")

    compatible_doors = []

    for _, door in tub_doors_df.iterrows():
        try:
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_height = door.get("Maximum Height") 
            door_series = door.get("Series")
            door_id = str(door.get("Unique ID", "")).strip()

            if not door_id:
                continue

            # Match criteria for tub doors
            if (
                pd.notna(tub_width) and pd.notna(tub_height) and
                pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_height) and
                door_min_width <= tub_width <= door_max_width and
                door_height <= tub_height and
                series_compatible(tub_series, door_series)
            ):
                logger.debug(f"✅ Found compatible tub door: {door_id} - {door.get('Product Name')}")
                
                # Format door data for the frontend
                door_data = door.to_dict()
                # Remove any NaN values
                door_data = {k: v for k, v in door_data.items() if pd.notna(v)}
                
                product_dict = {
                    "sku": door_id,
                    "is_combo": False,
                    "_ranking": door_data.get("Ranking", 999),
                    "name": door_data.get("Product Name", ""),
                    "image_url": image_handler.generate_image_url(door_data),
                    "product_page_url": door_data.get("Product Page URL", ""),
                    "nominal_dimensions": door_data.get("Nominal Dimensions", ""),
                    "brand": door_data.get("Brand", ""),
                    "series": door_data.get("Series", ""),
                    "glass_thickness": door_data.get("Glass Thickness", "") or door_data.get("Glass", ""),
                    "door_type": door_data.get("Door Type", "") or door_data.get("Door  Type", "") or door_data.get("Type", "")
                }
                compatible_doors.append(product_dict)
        except Exception as e:
            logger.error(f"Error processing tub door: {e}")

    # Add incompatibility reasons to the results if they exist
    for category, reason in incompatibility_reasons.items():
        results.append({
            "category": category,
            "incompatible_reason": reason
        })
    
    # Only add compatible products for categories without incompatibility reasons
    if compatible_doors and "Tub Doors" not in incompatibility_reasons:
        # Sort the doors by ranking
        sorted_doors = sorted(compatible_doors, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Tub Doors", "products": sorted_doors})

    return results