"""
Base Compatibility Module

This module provides functions to determine compatibility between shower bases and other products.
It enhances the product compatibility finder with additional relationships specific to shower bases.
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from .whitelist_helper import get_whitelist_for_sku

logger = logging.getLogger(__name__)

def _safe_notna(value) -> bool:
    """Safely check if a value is not NaN, handling pandas operations"""
    if value is None:
        return False
    try:
        return not pd.isna(value)
    except (TypeError, ValueError):
        return value is not None

def _safe_compare(val1, op, val2) -> bool:
    """Safely compare two values, handling pandas operations"""
    try:
        if not _safe_notna(val1) or not _safe_notna(val2):
            return False
        if op == "<=":
            return val1 <= val2
        elif op == ">=":
            return val1 >= val2
        elif op == "==":
            return val1 == val2
        elif op == "range":  # val1 <= val2 <= val3
            val3 = val2
            val2 = op
            return val1 <= val2 <= val3
        return False
    except (TypeError, ValueError):
        return False

def find_base_compatibilities(data, base_info):
    """
    Find compatible products for a shower base
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        base_info (dict): Dictionary containing base product information
        
    Returns:
        list: List of dictionaries containing category and compatible SKUs,
              or dictionaries with incompatibility reasons
    """
    try:
        # Try to get the SKU from various possible fields
        base_sku = (base_info.get("SKU") or 
                   base_info.get("sku") or 
                   base_info.get("Unique ID"))
        logger.info(f"Finding compatibilities for base SKU: {base_sku}")
        
        results = []
        incompatibility_reasons = {}

        # Check for incompatibility reasons
        doors_cant_fit_reason = base_info.get("Reason Doors Can't Fit")
        walls_cant_fit_reason = base_info.get("Reason Walls Can't Fit")

        # If there are specific reasons why doors or walls can't fit, add them to the incompatibility reasons
        try:
            if doors_cant_fit_reason and str(doors_cant_fit_reason).strip() not in ['', 'nan', 'None']:
                incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
                logger.info(
                    f"Shower doors incompatibility reason found: {doors_cant_fit_reason}"
                )
        except (AttributeError, TypeError):
            pass

        try:
            if walls_cant_fit_reason and str(walls_cant_fit_reason).strip() not in ['', 'nan', 'None']:
                incompatibility_reasons["Walls"] = walls_cant_fit_reason
                logger.info(
                    f"Walls incompatibility reason found: {walls_cant_fit_reason}")
        except (AttributeError, TypeError):
            pass

        # Get the base product details
        base_width = base_info.get("Max Door Width")
        base_install = str(base_info.get("Installation", "")).lower()
        base_series = base_info.get("Series")
        base_fit_return = base_info.get("Fits Return Panel Size")
        base_length = base_info.get("Length")
        base_width_actual = base_info.get("Width")
        base_nominal = base_info.get("Nominal Dimensions")
        base_brand = base_info.get("Brand")
        base_family = base_info.get("Family")

        # Check for incompatibility reasons
        doors_cant_fit_reason = base_info.get("Reason Doors Can't Fit")
        walls_cant_fit_reason = base_info.get("Reason Walls Can't Fit")

        # If there are specific reasons why doors or walls can't fit, add them to the incompatibility reasons
        if doors_cant_fit_reason and str(doors_cant_fit_reason) not in ['', 'nan', 'None']:
            incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
            logger.debug(
                f"Doors incompatibility reason found: {doors_cant_fit_reason}")

        if walls_cant_fit_reason and str(walls_cant_fit_reason) not in ['', 'nan', 'None']:
            incompatibility_reasons["Walls"] = walls_cant_fit_reason
            logger.debug(
                f"Walls incompatibility reason found: {walls_cant_fit_reason}")
        else:
            # Find compatible walls
            logger.info(f"Finding walls for base {base_sku} - Dimensions: {base_length} x {base_width_actual}")
            logger.info(f"Base brand: {base_brand}, Base family: {base_family}, Base series: {base_series}")
            logger.info(f"Base length: {base_length}, Base width: {base_width_actual}")
            logger.info(f"Base nominal: {base_nominal}")
            
            if "Walls" in data:
                walls_df = data["Walls"]
                logger.debug(f"Number of walls to check: {len(walls_df) if not walls_df.empty else 0}")

                compatible_walls = []

                # Get whitelist entries for this base SKU
                whitelist_skus = get_whitelist_for_sku(base_sku)
                whitelist_walls = []
                if whitelist_skus:
                    for wall_row in walls_df.itertuples():
                        wall_sku = getattr(wall_row, 'SKU', None)
                        if wall_sku in whitelist_skus:
                            whitelist_walls.append(wall_sku)

                for _, wall in walls_df.iterrows():
                    wall_sku = wall.get("SKU")
                    
                    # Check if this wall is whitelisted for this base
                    if wall_sku in whitelist_walls:
                        logger.info(f"✅ Whitelisted wall: {wall_sku} - {wall.get('Name', '')}")
                        wall_dict = wall.to_dict()
                        wall_dict["category"] = "Walls"
                        compatible_walls.append(wall_dict)
                        continue

                    wall_type = str(wall.get("Type", "")).lower()
                    wall_brand = wall.get("Brand")
                    wall_family = wall.get("Family")
                    wall_series = wall.get("Series")
                    wall_length = wall.get("Length")
                    wall_width = wall.get("Width")
                    wall_nominal = wall.get("Nominal Dimensions")
                    wall_cut_to_size = str(wall.get("Cut to Size", "")).lower()

                    logger.debug(f"  Checking wall {wall_sku}: {wall.get('Name', '')}")
                    logger.debug(f"    Wall type: {wall_type}")
                    logger.debug(f"    Wall dimensions: {wall_length} x {wall_width}")
                    logger.debug(f"    Wall nominal: {wall_nominal}")
                    logger.debug(f"    Cut to size: {wall_cut_to_size}")
                    logger.debug(f"    Wall brand: {wall_brand}, family: {wall_family}, series: {wall_series}")

                    # Type matching
                    type_match = ("alcove shower" in wall_type or "corner shower" in wall_type)
                    
                    # Installation matching
                    install_match = False
                    if "alcove" in base_install and "alcove shower" in wall_type:
                        install_match = True
                    elif "corner" in base_install and "corner shower" in wall_type:
                        install_match = True
                    elif "alcove/corner" in base_install and ("alcove shower" in wall_type or "corner shower" in wall_type):
                        install_match = True

                    # Brand/Family matching
                    brand_family_match = brand_family_match_func(base_brand, base_family, wall_brand, wall_family)
                    
                    # Series matching
                    series_match = series_compatible(base_series, wall_series)

                    logger.debug(f"    Type match: {type_match}")
                    logger.debug(f"    Install match: {install_match}")
                    logger.debug(f"    Brand/family match: {brand_family_match}")
                    logger.debug(f"    Series match: {series_match}")

                    if not (type_match and install_match and brand_family_match and series_match):
                        logger.debug(f"    ❌ Skipping wall {wall_sku} - basic criteria not met")
                        continue

                    # Dimensional matching
                    logger.debug(f"    ✅ Basic criteria met for wall {wall_sku}")

                    # Nominal match
                    if (_safe_notna(base_nominal) and _safe_notna(wall_nominal) and 
                        base_nominal == wall_nominal and wall_cut_to_size != "yes"):
                        logger.info(f"✅ Matched exact nominal wall: {wall_sku} - {wall.get('Name', '')}")
                        wall_dict = wall.to_dict()
                        wall_dict["category"] = "Walls"
                        compatible_walls.append(wall_dict)
                        continue

                    # Cut-to-size match
                    if (wall_cut_to_size == "yes" and 
                        _safe_notna(wall_length) and _safe_notna(wall_width) and 
                        _safe_notna(base_length) and _safe_notna(base_width_actual)):
                        
                        wall_length_val = float(wall_length) if _safe_notna(wall_length) else 0
                        wall_width_val = float(wall_width) if _safe_notna(wall_width) else 0
                        base_length_val = float(base_length) if _safe_notna(base_length) else 0
                        base_width_val = float(base_width_actual) if _safe_notna(base_width_actual) else 0
                        
                        if (wall_length_val >= base_length_val and wall_width_val >= base_width_val):
                            logger.info(f"✅ Matched cut-to-size wall: {wall_sku} - {wall.get('Name', '')}")
                            wall_dict = wall.to_dict()
                            wall_dict["category"] = "Walls"
                            compatible_walls.append(wall_dict)

                if compatible_walls:
                    results.append({
                        "category": "Walls",
                        "products": compatible_walls
                    })
                    logger.info(f"Found {len(compatible_walls)} compatible walls")
                else:
                    logger.info("No compatible walls found")

        # Find compatible shower doors 
        if "Shower Doors" not in incompatibility_reasons and "Shower Doors" in data:
            doors_df = data["Shower Doors"]
            logger.debug(f"Checking {len(doors_df)} shower doors for compatibility")

            compatible_doors = []

            # Get whitelist entries for this base SKU
            whitelist_skus = get_whitelist_for_sku(base_sku)
            whitelist_doors = []
            if whitelist_skus:
                for door_row in doors_df.itertuples():
                    door_sku = getattr(door_row, 'SKU', None)
                    if door_sku in whitelist_skus:
                        whitelist_doors.append(door_sku)

            for _, door in doors_df.iterrows():
                door_sku = door.get("SKU")
                
                # Check if this door is whitelisted for this base
                if door_sku in whitelist_doors:
                    logger.info(f"✅ Whitelisted door: {door_sku} - {door.get('Name', '')}")
                    door_dict = door.to_dict()
                    door_dict["category"] = "Shower Doors"
                    compatible_doors.append(door_dict)
                    continue

                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Min Width")
                door_max_width = door.get("Max Width")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                door_family = door.get("Family")
                door_has_return = str(door.get("Fits Return Panel Size", "")).lower()

                logger.debug(f"  Checking door {door_sku}: {door.get('Name', '')}")
                logger.debug(f"    Min Width: {door_min_width}, Max Width: {door_max_width}")
                logger.debug(f"    Door type: {door_type}, Has Return: {door_has_return}")
                logger.debug(f"    Series: {door_series}, Brand: {door_brand}, Family: {door_family}")

                # Alcove installation match
                try:
                    base_width_val = float(base_width) if _safe_notna(base_width) else None
                    door_min_val = float(door_min_width) if _safe_notna(door_min_width) else None
                    door_max_val = float(door_max_width) if _safe_notna(door_max_width) else None
                    
                    alcove_match = (
                        "alcove" in base_install 
                        and base_width_val is not None
                        and door_min_val is not None 
                        and door_max_val is not None
                        and door_min_val <= base_width_val <= door_max_val
                        and series_compatible(base_series, door_series))
                except (TypeError, ValueError):
                    alcove_match = False

                logger.debug(f"    Alcove match: {alcove_match}")

                # Corner installation match
                try:
                    corner_match = (
                        "corner" in base_install 
                        and _safe_notna(base_fit_return) 
                        and _safe_notna(door_has_return)
                        and str(base_fit_return).lower() == str(door_has_return).lower()
                        and series_compatible(base_series, door_series))
                except (TypeError, ValueError):
                    corner_match = False

                logger.debug(f"    Corner match: {corner_match}")

                if alcove_match or corner_match:
                    logger.debug(f"    ✅ Door {door_sku} is compatible")
                    door_dict = door.to_dict()
                    door_dict["category"] = "Shower Doors"
                    compatible_doors.append(door_dict)
                else:
                    logger.debug(f"    ❌ Door {door_sku} is not compatible")

            if compatible_doors:
                results.append({
                    "category": "Shower Doors",
                    "products": compatible_doors
                })
                logger.info(f"Found {len(compatible_doors)} compatible shower doors")
            else:
                logger.info("No compatible shower doors found")

        # Add incompatibility reasons for categories that have them
        for category, reason in incompatibility_reasons.items():
            results.append({
                "category": category,
                "incompatibility_reason": reason
            })

        return results

    except Exception as e:
        logger.error(f"Error in find_base_compatibilities: {e}")
        return []

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    if not base_series or not compare_series:
        return True
    
    try:
        base_series = str(base_series).strip() if base_series is not None else ""
        compare_series = str(compare_series).strip() if compare_series is not None else ""
        return base_series == compare_series
    except (AttributeError, TypeError):
        return True

def brand_family_match_func(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match"""
    if not base_brand or not wall_brand:
        return False
    
    try:
        base_brand = str(base_brand).strip() if base_brand is not None else ""
        wall_brand = str(wall_brand).strip() if wall_brand is not None else ""
        
        if base_brand != wall_brand:
            return False
        
        if base_family and wall_family:
            base_family = str(base_family).strip() if base_family is not None else ""
            wall_family = str(wall_family).strip() if wall_family is not None else ""
            return base_family == wall_family
        
        return True
    except (AttributeError, TypeError):
        return False