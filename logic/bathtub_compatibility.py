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
    # Convert to strings and normalize
    base_series = str(base_series).strip() if base_series else ""
    compare_series = str(compare_series).strip() if compare_series else ""
    
    # If either is empty, they're not compatible
    if not base_series or not compare_series:
        return False
        
    # Same series are always compatible
    if base_series.lower() == compare_series.lower():
        return True
        
    # Special case for Retail compatibility
    if base_series == "Retail" or compare_series == "Retail":
        # Retail is compatible with Retail, MAAX, and Swan
        other_series = compare_series if base_series == "Retail" else base_series
        return other_series in ["Retail", "MAAX", "Swan"]
        
    # MAAX compatibility rules
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
        
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
        
    # Swan series compatibility
    if base_series == "Swan" or compare_series == "Swan":
        # Swan is compatible with only Swan and Retail
        other_series = compare_series if base_series == "Swan" else base_series
        return other_series in ["Swan", "Retail"]
        
    # Default case - no other compatibility
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
    base_brand = str(base_brand).strip().lower() if base_brand else ""
    base_family = str(base_family).strip().lower() if base_family else ""
    wall_brand = str(wall_brand).strip().lower() if wall_brand else ""
    wall_family = str(wall_family).strip().lower() if wall_family else ""

    # First check for specifically restricted families
    if base_family == "olio" and wall_family != "olio":
        return False
    
    if wall_family == "olio" and base_family != "olio":
        return False
    
    if base_family == "vellamo" and wall_brand != "vellamo":
        return False
    
    if wall_family == "vellamo" and base_brand != "vellamo":
        return False
    
    if base_family == "interflo" and wall_brand != "interflo":
        return False
    
    if wall_family == "interflo" and base_brand != "interflo":
        return False

    # Check for special cases for specific families
    # Utile, Nextile and Versaline walls should only match with specific bathtub families
    if wall_family in ["utile", "nextile", "versaline"] and base_family not in ["nomad", "mackenzie", "exhibit", "new town", "rubix", "bosca", "cocoon", "corinthia"]:
        return False
    
    # Different brand checks
    if base_brand == "maax" and wall_brand != "maax":
        return False
    
    if base_brand == "swan" and wall_brand != "swan":
        return False
    
    if base_brand == "bootz" and wall_brand != "bootz":
        return False
    
    # If we passed all restrictions and brands match, we're compatible
    if base_brand == wall_brand:
        return True
            
    # Default case - no match
    return False


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
                    "image_url": door_data.get("Image URL", ""),
                    "nominal_dimensions": door_data.get("Nominal Dimensions", ""),
                    "brand": door_data.get("Brand", ""),
                    "series": door_data.get("Series", ""),
                    "glass_thickness": door_data.get("Glass Thickness", ""),
                    "door_type": door_data.get("Door Type", "")
                }
                compatible_doors.append(product_dict)
        except Exception as e:
            logger.error(f"Error processing tub door: {e}")
    
    def find_closest_walls(tub_length, tub_width, candidate_walls):
        """
        Find walls with the closest dimensions to the tub based on combined distance.
        """
        candidate_walls = candidate_walls.copy()
        candidate_walls["distance"] = (candidate_walls["Length"] - tub_length).abs() + (candidate_walls["Width"] - tub_width).abs()
        min_distance = candidate_walls["distance"].min()
        return candidate_walls[candidate_walls["distance"] == min_distance]

    # ---------- Walls ----------
    compatible_walls = []

    # Log some helpful debug info
    logger.info(f"Finding walls for bathtub {bathtub_info.get('Unique ID')} - Dimensions: {tub_nominal}")
    logger.info(f"Tub brand: {tub_brand}, Tub family: {tub_family}, Tub series: {tub_series}")
    logger.info(f"Tub length: {tub_length}, Tub width: {tub_width_actual}")

    # Step 1: exact nominal matches (Cut to Size != "Yes")
    nominal_walls = walls_df[
        (walls_df["Type"].str.lower().str.contains("tub", na=False)) &
        (walls_df["Cut to Size"] != "Yes") &
        (walls_df["Nominal Dimensions"] == tub_nominal) &
        (walls_df["Series"].apply(lambda x: series_compatible(tub_series, x))) &
        (walls_df.apply(lambda x: bathtub_brand_family_match(tub_brand, tub_family, x["Brand"], x["Family"]), axis=1))
    ]

    for _, wall in nominal_walls.iterrows():
        wall_id = str(wall.get("Unique ID", "")).strip()
        logger.info(f"✅ Matched exact nominal wall: {wall_id} - {wall.get('Product Name')}")
        wall_data = wall.to_dict()
        wall_data = {k: v for k, v in wall_data.items() if pd.notna(v)}
        compatible_walls.append({
            "sku": wall_id,
            "is_combo": False,
            "_ranking": wall_data.get("Ranking", 999),
            "name": wall_data.get("Product Name", ""),
            "image_url": wall_data.get("Image URL", ""),
            "nominal_dimensions": wall_data.get("Nominal Dimensions", ""),
            "brand": wall_data.get("Brand", ""),
            "series": wall_data.get("Series", ""),
            "family": wall_data.get("Family", "")
        })

    # Step 2: Cut to Size walls (only closest size)
    cut_walls_candidates = walls_df[
        (walls_df["Type"].str.lower().str.contains("tub", na=False)) &
        (walls_df["Cut to Size"] == "Yes") &
        (walls_df["Series"].apply(lambda x: series_compatible(tub_series, x))) &
        (walls_df.apply(lambda x: bathtub_brand_family_match(tub_brand, tub_family, x["Brand"], x["Family"]), axis=1)) &
        pd.notna(walls_df["Length"]) & pd.notna(walls_df["Width"])
    ]

    logger.info(f"Found {len(cut_walls_candidates)} cut-to-size wall candidates")
    if not cut_walls_candidates.empty and pd.notna(tub_length) and pd.notna(tub_width_actual):
        closest_cut_walls = find_closest_walls(tub_length, tub_width_actual, cut_walls_candidates)
        for _, wall in closest_cut_walls.iterrows():
            wall_id = str(wall.get("Unique ID", "")).strip()
            logger.info(f"✅ Matched closest cut wall: {wall_id} - {wall.get('Product Name')}")
            wall_data = wall.to_dict()
            wall_data = {k: v for k, v in wall_data.items() if pd.notna(v)}
            compatible_walls.append({
                "sku": wall_id,
                "is_combo": False,
                "_ranking": wall_data.get("Ranking", 999),
                "name": wall_data.get("Product Name", ""),
                "image_url": wall_data.get("Image URL", ""),
                "nominal_dimensions": wall_data.get("Nominal Dimensions", ""),
                "brand": wall_data.get("Brand", ""),
                "series": wall_data.get("Series", ""),
                "family": wall_data.get("Family", "")
            })
    
    # Sort products by ranking (lowest to highest) before adding to results
    if compatible_doors:
        # Sort the doors by ranking
        sorted_doors = sorted(compatible_doors, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Tub Doors", "products": sorted_doors})
    
    if compatible_walls:
        # Sort the walls by ranking
        sorted_walls = sorted(compatible_walls, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Walls", "products": sorted_walls})
    
    return results