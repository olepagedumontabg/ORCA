"""
Shower Compatibility Module

This module provides functions to determine compatibility between shower units and doors.
It enhances the product compatibility finder with additional relationships specific to showers.
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

def find_shower_compatibilities(data, shower_info):
    """
    Find compatible doors for a shower
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        shower_info (dict): Dictionary containing shower product information
        
    Returns:
        list: List of dictionaries containing category and compatible products
              or dictionaries with incompatibility reasons
    """
    results = []
    incompatibility_reasons = {}
    
    # Check for incompatibility reasons
    doors_cant_fit_reason = shower_info.get("Reason Doors Can't Fit")
    
    # If there are specific reasons why doors can't fit, add them to the incompatibility reasons
    if pd.notna(doors_cant_fit_reason) and doors_cant_fit_reason:
        incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
        logger.info(f"Shower doors incompatibility reason found: {doors_cant_fit_reason}")

    # Check if necessary data exists
    if 'Shower Doors' not in data:
        logger.warning("Missing Shower Doors sheet")
        
        # Still add incompatibility reasons even if missing sheets
        for category, reason in incompatibility_reasons.items():
            results.append({
                "category": category,
                "incompatible_reason": reason
            })
        return results

    doors_df = data['Shower Doors']
    
    # Get shower properties
    shower_width = shower_info.get("Max Door Width")
    shower_height = shower_info.get("Max Door Height")
    shower_install = shower_info.get("Installation")
    shower_series = shower_info.get("Series")
    
    logger.debug(f"Finding doors for shower {shower_info.get('Unique ID')} - {shower_info.get('Product Name')}")
    logger.debug(f"Shower properties: Width={shower_width}, Height={shower_height}, Install={shower_install}, Series={shower_series}")

    compatible_doors = []

    for _, door in doors_df.iterrows():
        try:
            door_type = str(door.get("Type", "")).lower()
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_height = door.get("Maximum Height") 
            door_series = door.get("Series")
            door_id = str(door.get("Unique ID", "")).strip()

            if not door_id:
                continue

            # Match criteria for alcove installation showers
            if (
                shower_install == "Alcove" and
                pd.notna(shower_width) and pd.notna(shower_height) and
                pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_height) and
                door_min_width <= shower_width <= door_max_width and
                door_height <= shower_height and
                series_compatible(shower_series, door_series)
            ):
                logger.debug(f"✅ Found compatible door: {door_id} - {door.get('Product Name')}")
                
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
                    "nominal_dimensions": door_data.get("Nominal Dimensions", ""),
                    "brand": door_data.get("Brand", ""),
                    "series": door_data.get("Series", ""),
                    "glass_thickness": door_data.get("Glass Thickness", ""),
                    "door_type": door_data.get("Door Type", "")
                }
                compatible_doors.append(product_dict)
        except Exception as e:
            logger.error(f"Error processing shower door: {e}")

    # Add incompatibility reasons to the results if they exist
    for category, reason in incompatibility_reasons.items():
        results.append({
            "category": category,
            "incompatible_reason": reason
        })
    
    # Only add compatible products for categories without incompatibility reasons
    if compatible_doors and "Shower Doors" not in incompatibility_reasons:
        # Sort the doors by ranking
        sorted_doors = sorted(compatible_doors, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Shower Doors", "products": sorted_doors})

    return results