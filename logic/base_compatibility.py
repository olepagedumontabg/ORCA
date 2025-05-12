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
        
        # Set tolerances
        tolerance = 2  # inches
        wall_tolerance = 3  # inches for Walls
        
        # ---------- Doors ----------
        if 'Shower Doors' in data:
            doors_df = data['Shower Doors']
            matching_doors = []
            
            for _, door in doors_df.iterrows():
                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_has_return = door.get("Has Return Panel")
                door_family = door.get("Family")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                door_id = str(door.get("Unique ID", "")).strip()

                if (
                    "shower" in door_type and
                    "alcove" in base_install and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    series_compatible(base_series, door_series) and
                    brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    if door_id:
                        matching_doors.append(door_id)

                if (
                    "shower" in door_type and
                    "corner" in base_install and
                    door_has_return == "Yes" and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    series_compatible(base_series, door_series) and
                    brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    # For corner installations with return panels, we need to check return panel compatibility
                    if 'Return Panels' in data:
                        panels_df = data['Return Panels']
                        for _, panel in panels_df.iterrows():
                            panel_size = panel.get("Return Panel Size")
                            panel_family = panel.get("Family")
                            panel_brand = panel.get("Brand")
                            panel_id = str(panel.get("Unique ID", "")).strip()

                            if (
                                base_fit_return == panel_size and
                                brand_family_match_doors(base_brand, base_family, panel_brand, panel_family) and
                                door_id and panel_id
                            ):
                                matching_doors.append(f"{door_id}|{panel_id}")
            
            if matching_doors:
                compatible_products.append({
                    "category": "Shower Doors",
                    "skus": matching_doors
                })
        
        # ---------- Enclosures ----------
        if 'Enclosures' in data and "corner" in base_install:
            enclosures_df = data['Enclosures']
            matching_enclosures = []
            
            for _, enclosure in enclosures_df.iterrows():
                enc_series = enclosure.get("Series")
                enc_nominal = enclosure.get("Nominal Dimensions")
                enc_door_width = enclosure.get("Door Width")
                enc_return_width = enclosure.get("Return Panel Width")
                enc_brand = enclosure.get("Brand")
                enc_family = enclosure.get("Family")
                enc_id = str(enclosure.get("Unique ID", "")).strip()

                if not enc_id:
                    continue

                if not (
                    series_compatible(base_series, enc_series) and
                    brand_family_match_doors(base_brand, base_family, enc_brand, enc_family)
                ):
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
                    matching_enclosures.append(enc_id)
            
            if matching_enclosures:
                compatible_products.append({
                    "category": "Enclosures",
                    "skus": matching_enclosures
                })
        
        # ---------- Walls ----------
        if 'Walls' in data:
            walls_df = data['Walls']
            matching_walls = []
            
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
                    brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
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
                    brand_family_match_walls(base_brand, base_family, wall_brand, wall_family) and
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

def brand_family_match_doors(base_brand, base_family, other_brand, other_family):
    """Check if brands and families match for doors"""
    return (
        (base_brand == "Maax" and other_brand == "Maax") or
        (base_brand == "Neptune" and other_brand == "Neptune") or
        (base_brand == "Aker" and other_brand == "Maax")
    )

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for walls"""
    brand_match = (
        (base_brand == "Swan" and wall_brand == "Swan") or
        (base_brand == "Neptune" and wall_brand == "Neptune") or
        (base_brand == "Bootz" and wall_brand == "Bootz") or
        (base_family == "W&B" and wall_family == "W&B") or
        (base_family == "Olio" and wall_family == "Olio") or
        (base_family == "Vellamo" and wall_brand == "Vellamo")
    )
    
    maax_match = (
        (base_brand == "Maax" and wall_brand == "Maax") and 
        (
            (base_family == "B3" and wall_family in ["Utile", "Denso", "Nextile", "Versaline"]) or
            (base_family in ["Finesse", "Distinct", "Zone", "Olympia", "Icon"] and 
             wall_family in ["Utile", "Denso", "Nextile", "Versaline"])
        )
    )
    
    return brand_match or maax_match