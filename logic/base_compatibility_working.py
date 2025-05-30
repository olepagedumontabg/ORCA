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
        base_sku = base_info.get("SKU") or base_info.get("sku")
        logger.info(f"Finding compatibilities for base SKU: {base_sku}")
        
        results = []
        incompatibility_reasons = {}

        # Check for incompatibility reasons
        doors_cant_fit_reason = base_info.get("Reason Doors Can't Fit")
        walls_cant_fit_reason = base_info.get("Reason Walls Can't Fit")

        # Handle incompatibility reasons safely
        if doors_cant_fit_reason is not None:
            reason_str = str(doors_cant_fit_reason).strip()
            if reason_str and reason_str not in ['', 'nan', 'None']:
                incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
                logger.info(f"Shower doors incompatibility reason found: {doors_cant_fit_reason}")

        if walls_cant_fit_reason is not None:
            reason_str = str(walls_cant_fit_reason).strip()
            if reason_str and reason_str not in ['', 'nan', 'None']:
                incompatibility_reasons["Walls"] = walls_cant_fit_reason
                logger.info(f"Walls incompatibility reason found: {walls_cant_fit_reason}")

        # Get the base product details with safe conversion
        base_width = base_info.get("Max Door Width")
        base_install = str(base_info.get("Installation", "")).lower() if base_info.get("Installation") else ""
        base_series = base_info.get("Series")
        base_fit_return = base_info.get("Fits Return Panel Size")
        base_length = base_info.get("Length")
        base_width_actual = base_info.get("Width")
        base_nominal = base_info.get("Nominal Dimensions")
        base_brand = base_info.get("Brand")
        base_family = base_info.get("Family")

        # Find compatible walls if no incompatibility reason
        if "Walls" not in incompatibility_reasons and "Walls" in data:
            logger.info(f"Finding walls for base {base_sku} - Dimensions: {base_length} x {base_width_actual}")
            logger.info(f"Base brand: {base_brand}, Base family: {base_family}, Base series: {base_series}")
            logger.info(f"Base length: {base_length}, Base width: {base_width_actual}")
            logger.info(f"Base nominal: {base_nominal}")
            
            walls_df = data["Walls"]
            logger.debug(f"Number of walls to check: {len(walls_df) if not walls_df.empty else 0}")

            nominal_matches = []
            cut_candidates = []

            for _, wall in walls_df.iterrows():
                wall_type = str(wall.get("Type", "")).lower()
                wall_brand = wall.get("Brand")
                wall_family = wall.get("Family")
                wall_series = wall.get("Series")
                wall_length = wall.get("Length")
                wall_width = wall.get("Width")
                wall_nominal = wall.get("Nominal Dimensions")
                wall_cut_to_size = str(wall.get("Cut to Size", "")).lower()

                # Type matching
                if not ("alcove shower" in wall_type or "corner shower" in wall_type):
                    continue
                
                # Installation matching
                install_match = False
                if "alcove" in base_install and "alcove shower" in wall_type:
                    install_match = True
                elif "corner" in base_install and "corner shower" in wall_type:
                    install_match = True
                elif "alcove/corner" in base_install and ("alcove shower" in wall_type or "corner shower" in wall_type):
                    install_match = True

                if not install_match:
                    continue

                # Brand/Family matching
                if not brand_family_match(base_brand, base_family, wall_brand, wall_family):
                    continue

                # Series matching
                if not series_compatible(base_series, wall_series):
                    continue

                # Dimensional matching
                wall_id = wall.get("Wall ID")
                
                # Nominal match
                if (base_nominal is not None and wall_nominal is not None and 
                    str(base_nominal) == str(wall_nominal) and wall_cut_to_size != "yes"):
                    logger.info(f"✅ Matched exact nominal wall: {wall.get('SKU')} - {wall.get('Name', '')}")
                    nominal_matches.append(wall_id)
                    continue

                # Cut-to-size match
                if (wall_cut_to_size == "yes" and 
                    wall_length is not None and wall_width is not None and 
                    base_length is not None and base_width_actual is not None):
                    
                    try:
                        wall_length_val = float(wall_length)
                        wall_width_val = float(wall_width)
                        base_length_val = float(base_length)
                        base_width_val = float(base_width_actual)
                        
                        if wall_length_val >= base_length_val and wall_width_val >= base_width_val:
                            cut_candidates.append({
                                "id": wall_id,
                                "length": wall_length_val,
                                "width": wall_width_val
                            })
                    except (ValueError, TypeError):
                        continue

            # Select closest cut size walls
            closest_cut_ids = []
            if cut_candidates:
                min_len = min(c["length"] for c in cut_candidates)
                min_w = min(c["width"] for c in cut_candidates if c["length"] == min_len)
                closest_cut_ids = [
                    c["id"] for c in cut_candidates
                    if c["length"] == min_len and c["width"] == min_w
                ]

            # Convert wall IDs to product dictionaries
            all_wall_ids = nominal_matches + closest_cut_ids
            
            compatible_walls = []
            for wall_id in all_wall_ids:
                try:
                    wall_id_int = int(wall_id) if wall_id is not None else None
                    if wall_id_int is not None:
                        wall_match = walls_df[walls_df["Wall ID"] == wall_id_int]
                        if not wall_match.empty:
                            wall_dict = wall_match.iloc[0].to_dict()
                            wall_dict["category"] = "Walls"
                            compatible_walls.append(wall_dict)
                except (ValueError, TypeError):
                    continue

            if compatible_walls:
                results.append({
                    "category": "Walls",
                    "products": compatible_walls
                })
                logger.info(f"Found {len(compatible_walls)} compatible walls")

        # Find compatible shower doors
        if "Shower Doors" not in incompatibility_reasons and "Shower Doors" in data:
            doors_df = data["Shower Doors"]
            logger.debug(f"Checking {len(doors_df)} shower doors for compatibility")

            compatible_doors = []

            for _, door in doors_df.iterrows():
                door_sku = door.get("SKU")
                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Min Width")
                door_max_width = door.get("Max Width")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                door_family = door.get("Family")
                door_has_return = str(door.get("Fits Return Panel Size", "")).lower()

                # Alcove installation match
                alcove_match = False
                if "alcove" in base_install:
                    try:
                        if (base_width is not None and door_min_width is not None and door_max_width is not None):
                            base_width_val = float(base_width)
                            door_min_val = float(door_min_width)
                            door_max_val = float(door_max_width)
                            if (door_min_val <= base_width_val <= door_max_val and 
                                series_compatible(base_series, door_series)):
                                alcove_match = True
                    except (ValueError, TypeError):
                        pass

                # Corner installation match
                corner_match = False
                if ("corner" in base_install and 
                    base_fit_return is not None and door_has_return and
                    str(base_fit_return).lower() == door_has_return and
                    series_compatible(base_series, door_series)):
                    corner_match = True

                if alcove_match or corner_match:
                    door_dict = door.to_dict()
                    door_dict["category"] = "Shower Doors"
                    compatible_doors.append(door_dict)

            if compatible_doors:
                results.append({
                    "category": "Shower Doors",
                    "products": compatible_doors
                })
                logger.info(f"Found {len(compatible_doors)} compatible shower doors")

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
    
    base_series = str(base_series).strip() if base_series is not None else ""
    compare_series = str(compare_series).strip() if compare_series is not None else ""
    
    if not base_series or not compare_series:
        return True
    if base_series.lower() == compare_series.lower():
        return True
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match"""
    if not base_brand or not wall_brand:
        return False
    
    base_brand = str(base_brand).strip() if base_brand is not None else ""
    wall_brand = str(wall_brand).strip() if wall_brand is not None else ""
    
    if base_brand != wall_brand:
        return False
    
    if base_family and wall_family:
        base_family = str(base_family).strip() if base_family is not None else ""
        wall_family = str(wall_family).strip() if wall_family is not None else ""
        return base_family == wall_family
    
    return True