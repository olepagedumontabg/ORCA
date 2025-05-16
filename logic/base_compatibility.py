import pandas as pd
import logging
from logic.incompatibility_rules import is_incompatible

# Configure logging
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
        compatible_products = []
        incompatibility_reasons = {}

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
        if pd.notna(doors_cant_fit_reason) and doors_cant_fit_reason:
            incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
            logger.info(f"Doors incompatibility reason found: {doors_cant_fit_reason}")
            
        if pd.notna(walls_cant_fit_reason) and walls_cant_fit_reason:
            incompatibility_reasons["Walls"] = walls_cant_fit_reason
            logger.info(f"Walls incompatibility reason found: {walls_cant_fit_reason}")

        # Debug output for base product details
        logger.debug(f"Base compatibility details:")
        logger.debug(
            f"  Base: {base_info.get('Unique ID')} - {base_info.get('Product Name')}"
        )
        logger.debug(f"  Max Door Width: {base_width}")
        logger.debug(f"  Installation: {base_install}")
        logger.debug(f"  Series: {base_series}")
        logger.debug(f"  Brand: {base_brand}")
        logger.debug(f"  Family: {base_family}")
        logger.debug(
            f"  Dimensions: {base_nominal} ({base_length} x {base_width_actual})"
        )

        # Set tolerances
        tolerance = 2  # inches
        wall_tolerance = 3  # inches for Walls

        # Track matches for each category
        matching_doors = []
        matching_walls = []

        # ---------- Doors ----------
        if 'Shower Doors' in data:
            doors_df = data['Shower Doors']
            logger.debug(
                f"Checking compatibility with {len(doors_df)} shower doors")

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
                logger.debug(
                    f"    Min Width: {door_min_width}, Max Width: {door_max_width}"
                )
                logger.debug(
                    f"    Door type: {door_type}, Has Return: {door_has_return}"
                )
                logger.debug(
                    f"    Series: {door_series}, Brand: {door_brand}, Family: {door_family}"
                )

                # Alcove installation match
                alcove_match = (
                    # Don't check door_type for now as it might be missing
                    # "shower" in door_type and
                    "alcove" in base_install and pd.notna(base_width)
                    and pd.notna(door_min_width) and pd.notna(door_max_width)
                    and door_min_width <= base_width <= door_max_width
                    and series_compatible(base_series, door_series))

                logger.debug(f"    Alcove match: {alcove_match}")
                logger.debug(
                    f"    Door width range: {door_min_width} <= {base_width} <= {door_max_width}: {door_min_width <= base_width <= door_max_width if pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) else 'Cannot compare'}"
                )
                logger.debug(
                    f"    Series match: {series_compatible(base_series, door_series)}"
                )

                if alcove_match:
                    if door_id:
                        matching_doors.append(door_id)
                        logger.debug(
                            f"    ✓ Added door {door_id} to matching doors")

                # Corner installation match with return panel
                corner_match = (
                    # Don't check door_type for now as it might be missing
                    # "shower" in door_type and
                    "corner" in base_install and door_has_return == "Yes"
                    and pd.notna(base_width) and pd.notna(door_min_width)
                    and pd.notna(door_max_width)
                    and door_min_width <= base_width <= door_max_width
                    and series_compatible(base_series, door_series))

                logger.debug(f"    Corner match: {corner_match}")
                if corner_match:
                    # For corner installations with return panels, we need to check return panel compatibility
                    if 'Return Panels' in data:
                        panels_df = data['Return Panels']
                        logger.debug(
                            f"    Checking {len(panels_df)} return panels for compatibility"
                        )

                        for _, panel in panels_df.iterrows():
                            panel_size = panel.get("Return Panel Size")
                            panel_family = panel.get("Family")
                            panel_id = str(panel.get("Unique ID", "")).strip()
                            panel_name = panel.get("Product Name", "")

                            logger.debug(
                                f"      Return panel: {panel_id} - {panel_name}"
                            )
                            logger.debug(
                                f"      Panel size: {panel_size}, Family: {panel_family}"
                            )

                            # Check panel compatibility for corner installation
                            panel_match = (pd.notna(base_fit_return)
                                           and pd.notna(panel_size)
                                           and base_fit_return == panel_size
                                           and door_family == panel_family
                                           and door_id and panel_id)

                            logger.debug(f"      Panel match: {panel_match}")
                            logger.debug(
                                f"      Base fits return panel size: {base_fit_return} == {panel_size}: {base_fit_return == panel_size if pd.notna(base_fit_return) and pd.notna(panel_size) else 'Cannot compare'}"
                            )
                            logger.debug(
                                f"      Door family match: {door_family} == {panel_family}: {door_family == panel_family if door_family and panel_family else 'Cannot compare'}"
                            )

                            if panel_match:
                                combo_id = f"{door_id}|{panel_id}"
                                matching_doors.append(combo_id)
                                logger.debug(
                                    f"      ✓ Added combo product {combo_id} to matching doors"
                                )

        # ---------- Enclosures ----------
        if 'Enclosures' in data and "corner" in base_install:
            enclosures_df = data['Enclosures']
            logger.debug(
                f"Checking compatibility with {len(enclosures_df)} enclosures")

            for _, enclosure in enclosures_df.iterrows():
                enc_series = enclosure.get("Series")
                enc_nominal = enclosure.get("Nominal Dimensions")
                enc_door_width = enclosure.get("Door Width")
                enc_return_width = enclosure.get("Return Panel Width")
                enc_id = str(enclosure.get("Unique ID", "")).strip()
                enc_name = enclosure.get("Product Name", "")

                logger.debug(f"  Checking enclosure: {enc_id} - {enc_name}")
                logger.debug(
                    f"    Series: {enc_series}, Nominal Dimensions: {enc_nominal}"
                )
                logger.debug(
                    f"    Door Width: {enc_door_width}, Return Width: {enc_return_width}"
                )
                logger.debug(
                    f"    Base nominal: {base_nominal}, Base size: {base_length} x {base_width_actual}"
                )

                if not enc_id:
                    logger.debug(f"    ✗ Skipping enclosure with no ID")
                    continue

                series_match = series_compatible(base_series, enc_series)
                logger.debug(f"    Series match: {series_match}")

                if not series_match:
                    logger.debug(
                        f"    ✗ Skipping enclosure due to series mismatch")
                    continue

                nominal_match = base_nominal == enc_nominal
                logger.debug(f"    Nominal dimensions match: {nominal_match}")

                dimension_match = (
                    pd.notna(base_length) and pd.notna(enc_door_width)
                    and pd.notna(base_width_actual)
                    and pd.notna(enc_return_width)
                    and base_length >= enc_door_width
                    and (base_length - enc_door_width) <= tolerance
                    and base_width_actual >= enc_return_width
                    and (base_width_actual - enc_return_width) <= tolerance)

                logger.debug(f"    Dimension match calculations:")
                if pd.notna(base_length) and pd.notna(enc_door_width):
                    logger.debug(
                        f"      Door width check: {base_length} >= {enc_door_width}: {base_length >= enc_door_width}"
                    )
                    logger.debug(
                        f"      Door tolerance check: {base_length} - {enc_door_width} <= {tolerance}: {(base_length - enc_door_width) <= tolerance if base_length >= enc_door_width else 'N/A'}"
                    )
                else:
                    logger.debug(
                        f"      Door width check: Cannot compare (missing data)"
                    )

                if pd.notna(base_width_actual) and pd.notna(enc_return_width):
                    logger.debug(
                        f"      Return width check: {base_width_actual} >= {enc_return_width}: {base_width_actual >= enc_return_width}"
                    )
                    logger.debug(
                        f"      Return tolerance check: {base_width_actual} - {enc_return_width} <= {tolerance}: {(base_width_actual - enc_return_width) <= tolerance if base_width_actual >= enc_return_width else 'N/A'}"
                    )
                else:
                    logger.debug(
                        f"      Return width check: Cannot compare (missing data)"
                    )

                logger.debug(f"    Overall dimension match: {dimension_match}")

                if nominal_match or dimension_match:
                    matching_doors.append(enc_id)
                    logger.debug(
                        f"    ✓ Added enclosure {enc_id} to matching doors")

        # ---------- Walls ----------
        if 'Walls' in data:
            walls_df = data['Walls']

            nominal_matches = []
            cut_candidates = []

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

                alcove_match = (
                    "alcove shower" in wall_type
                    and (base_install in ["alcove", "alcove or corner"])
                    and series_compatible(base_series, wall_series)
                    and brand_family_match(base_brand, base_family, wall_brand,
                                           wall_family))

                corner_match = (
                    "corner shower" in wall_type
                    and (base_install in ["corner", "alcove or corner"])
                    and series_compatible(base_series, wall_series)
                    and brand_family_match(base_brand, base_family, wall_brand,
                                           wall_family))

                if not (alcove_match or corner_match):
                    continue

                # ✅ Nominal match ONLY if Cut to Size is not Yes
                if base_nominal == wall_nominal and wall_cut != "Yes":
                    nominal_matches.append(wall_id)

                # ✅ Cut to size candidate
                elif wall_cut == "Yes" and pd.notna(base_length) and pd.notna(base_width_actual) \
                    and pd.notna(wall_length) and pd.notna(wall_width) \
                    and wall_length >= base_length and wall_width >= base_width_actual:
                    cut_candidates.append({
                        "id": wall_id,
                        "length": wall_length,
                        "width": wall_width
                    })

            # ✅ Select closest cut size walls
            closest_cut_ids = []
            if cut_candidates:
                min_length = min(c["length"] for c in cut_candidates)
                min_width = min(c["width"] for c in cut_candidates
                                if c["length"] == min_length)
                closest_cut_ids = [
                    c["id"] for c in cut_candidates
                    if c["length"] == min_length and c["width"] == min_width
                ]

            # ✅ Add all matches
            matching_walls.extend(nominal_matches + closest_cut_ids)

        # Add incompatibility reasons to the result if they exist
        for category, reason in incompatibility_reasons.items():
            compatible_products.append({
                "category": category,
                "incompatible_reason": reason
            })
            
        # If there are incompatibility reasons for a category, don't add compatible products for that category
        if matching_doors and "Shower Doors" not in incompatibility_reasons:
            compatible_products.append({
                "category": "Shower Doors",
                "skus": matching_doors
            })

        if matching_walls and "Walls" not in incompatibility_reasons:
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
        return compare_series in [
            "Retail", "MAAX", "Collection", "Professional"
        ]
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
    return ((base_brand == "swan" and wall_brand == "swan")
            or (base_brand == "neptune" and wall_brand == "neptune")
            or (base_brand == "bootz" and wall_brand == "bootz")
            or (base_family == "w&b" and wall_family == "w&b")
            or (base_family == "olio" and wall_family == "olio")
            or (base_family == "vellamo" and wall_family == "vellamo")
            or (base_family == "interflo" and wall_family == "interflo")
            or (base_family == "b3"
                and wall_family in ["utile", "denso", "nextile", "versaline"])
            or (base_family
                in ["finesse", "distinct", "zone", "olympia", "icon", "roka"]
                and wall_family in ["utile", "nextile"]))
