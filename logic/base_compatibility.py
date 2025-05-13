import pandas as pd
import logging

# Configure logging
logger = logging.getLogger(__name__)

def find_base_compatibilities(data, base_info):
    """
    Find compatible products for a shower base
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        base_info (dict): Dictionary containing base product information
        
    Returns:
        list: List of dictionaries containing category and compatible SKUs
    """
    try:
        compatible_products = []
        
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
        
        # Debug output for base product details
        logger.debug(f"Base compatibility details:")
        logger.debug(f"  Base: {base_info.get('Unique ID')} - {base_info.get('Product Name')}")
        logger.debug(f"  Max Door Width: {base_width}")
        logger.debug(f"  Installation: {base_install}")
        logger.debug(f"  Series: {base_series}")
        logger.debug(f"  Brand: {base_brand}")
        logger.debug(f"  Family: {base_family}")
        logger.debug(f"  Dimensions: {base_nominal} ({base_length} x {base_width_actual})")
        
        # Set tolerances
        tolerance = 2  # inches
        wall_tolerance = 3  # inches for Walls
        
        # Track matches for each category
        matching_doors = []
        matching_walls = []
        
        # ---------- Doors ----------
        if 'Shower Doors' in data:
            doors_df = data['Shower Doors']
            logger.debug(f"Checking compatibility with {len(doors_df)} shower doors")
            
            for _, door in doors_df.iterrows():
                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_has_return = door.get("Has Return Panel")
                door_family = door.get("Family")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                door_id = str(door.get("Unique ID", "")).strip()
                door_name = door.get("Product Name", "")
                
                logger.debug(f"  Checking door: {door_id} - {door_name}")
                logger.debug(f"    Min Width: {door_min_width}, Max Width: {door_max_width}")
                logger.debug(f"    Door type: {door_type}, Has Return: {door_has_return}")
                logger.debug(f"    Series: {door_series}, Brand: {door_brand}, Family: {door_family}")

                # Alcove installation match
                alcove_match = (
                    # Don't check door_type for now as it might be missing
                    # "shower" in door_type and
                    "alcove" in base_install and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    series_compatible(base_series, door_series)
                )
                
                logger.debug(f"    Alcove match: {alcove_match}")
                logger.debug(f"    Door width range: {door_min_width} <= {base_width} <= {door_max_width}: {door_min_width <= base_width <= door_max_width if pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) else 'Cannot compare'}")
                logger.debug(f"    Series match: {series_compatible(base_series, door_series)}")
                
                if alcove_match:
                    if door_id:
                        matching_doors.append(door_id)
                        logger.debug(f"    ✓ Added door {door_id} to matching doors")

                # Corner installation match with return panel
                if (
                    "shower" in door_type and
                    "corner" in base_install and
                    door_has_return == "Yes" and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    series_compatible(base_series, door_series)
                ):
                    # For corner installations with return panels, we need to check return panel compatibility
                    if 'Return Panels' in data:
                        panels_df = data['Return Panels']
                        for _, panel in panels_df.iterrows():
                            panel_size = panel.get("Return Panel Size")
                            panel_family = panel.get("Family")
                            panel_id = str(panel.get("Unique ID", "")).strip()

                            if (
                                base_fit_return == panel_size and
                                door_family == panel_family and
                                door_id and panel_id
                            ):
                                matching_doors.append(f"{door_id}|{panel_id}")
            
        # ---------- Enclosures ----------
        if 'Enclosures' in data and "corner" in base_install:
            enclosures_df = data['Enclosures']
            
            for _, enclosure in enclosures_df.iterrows():
                enc_series = enclosure.get("Series")
                enc_nominal = enclosure.get("Nominal Dimensions")
                enc_door_width = enclosure.get("Door Width")
                enc_return_width = enclosure.get("Return Panel Width")
                enc_id = str(enclosure.get("Unique ID", "")).strip()

                if not enc_id:
                    continue

                if not series_compatible(base_series, enc_series):
                    continue

                nominal_match = base_nominal == enc_nominal

                dimension_match = (
                    pd.notna(base_length) and pd.notna(enc_door_width) and
                    pd.notna(base_width_actual) and pd.notna(enc_return_width) and
                    base_length >= enc_door_width and
                    (base_length - enc_door_width) <= tolerance and
                    base_width_actual >= enc_return_width and
                    (base_width_actual - enc_return_width) <= tolerance
                )

                if nominal_match or dimension_match:
                    matching_doors.append(enc_id)
        
        # ---------- Walls ----------
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

                alcove_match = (
                    "alcove shower" in wall_type and
                    (base_install in ["alcove", "alcove or corner"]) and
                    series_compatible(base_series, wall_series) and
                    brand_family_match(base_brand, base_family, wall_brand, wall_family) and
                    (
                        base_nominal == wall_nominal or
                        (wall_cut == "Yes" and
                         pd.notna(base_length) and pd.notna(wall_length) and
                         pd.notna(base_width_actual) and pd.notna(wall_width) and
                         base_length <= wall_length and
                         abs(base_length - wall_length) <= wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= wall_tolerance)
                    )
                )

                corner_match = (
                    "corner shower" in wall_type and
                    (base_install in ["corner", "alcove or corner"]) and
                    series_compatible(base_series, wall_series) and
                    brand_family_match(base_brand, base_family, wall_brand, wall_family) and
                    (
                        base_nominal == wall_nominal or
                        (wall_cut == "Yes" and
                         pd.notna(base_length) and pd.notna(wall_length) and
                         pd.notna(base_width_actual) and pd.notna(wall_width) and
                         base_length <= wall_length and
                         abs(base_length - wall_length) <= wall_tolerance and
                         base_width_actual <= wall_width and
                         abs(base_width_actual - wall_width) <= wall_tolerance)
                    )
                )

                if wall_id and (alcove_match or corner_match):
                    matching_walls.append(wall_id)
            
        # Add results to the compatible_products list
        if matching_doors:
            compatible_products.append({
                "category": "Shower Doors",
                "skus": matching_doors
            })
            
        if matching_walls:
            compatible_products.append({
                "category": "Walls",
                "skus": matching_walls
            })
        
        return compatible_products
    
    except Exception as e:
        logger.error(f"Error in find_base_compatibilities: {str(e)}")
        return []

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match"""
    base_brand = str(base_brand).strip().lower()
    base_family = str(base_family).strip().lower()
    wall_brand = str(wall_brand).strip().lower()
    wall_family = str(wall_family).strip().lower()

    # Rule 1: If Base Brand is maax, Wall Brand MUST be maax
    if base_brand == "maax" and wall_brand != "maax":
        return False

    # Rule 2: After passing Rule 1, check families + other brand matches
    return (
        (base_brand == "swan" and wall_brand == "swan") or
        (base_brand == "neptune" and wall_brand == "neptune") or
        (base_brand == "bootz" and wall_brand == "bootz") or
        (base_family == "w&b" and wall_family == "w&b") or
        (base_family == "olio" and wall_family == "olio") or
        (base_family == "b3" and wall_family in ["utile", "denso", "nextile", "versaline"]) or
        (base_family in ["finesse", "distinct", "zone", "olympia", "icon"] and
         wall_family in ["utile", "denso", "nextile", "versaline"])
    )