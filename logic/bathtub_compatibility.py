import logging
import pandas as pd
from logic import image_handler

logger = logging.getLogger(__name__)

# Constants
TOLERANCE_INCHES = 3  # 3 inches tolerance for dimension matching


def series_compatible(base_series, compare_series, base_brand=None, compare_brand=None):
    """
    Check if two series are compatible based on business rules.

    Args:
        base_series (str): Series of the base product
        compare_series (str): Series of the product to compare with
        base_brand (str): Brand of the base product (optional)
        compare_brand (str): Brand of the compare product (optional)

    Returns:
        bool: True if the series are compatible, False otherwise
    """
    # Convert to strings and normalize
    base_series = str(base_series).strip() if base_series else ""
    compare_series = str(compare_series).strip() if compare_series else ""
    base_brand = str(base_brand).strip().lower() if base_brand else ""
    compare_brand = str(compare_brand).strip().lower() if compare_brand else ""

    # Universal compatibility: DreamLine and Swan are compatible with any series
    if compare_brand in ["dreamline", "swan"] or base_brand in ["dreamline", "swan"]:
        return True

    # If either series is empty, they're compatible (relaxed rule for cross-brand compatibility)
    if not base_series or not compare_series:
        return True

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

    # Universal compatibility: Dreamline and Swan are compatible with anything
    if base_brand in ["dreamline", "swan"] or wall_brand in ["dreamline", "swan"]:
        return True

    # First check for specifically restricted families
    if base_family == "olio" and wall_family != "olio":
        return False

    if wall_family == "olio" and base_family != "olio":
        return False

    if base_family == "vellamo" and wall_brand != "vellamo":
        return False

    if wall_family == "vellamo" and base_brand != "vellamo":
        return False

    if base_family == "interflo" and wall_family != "interflo":
        return False

    if wall_family == "interflo" and base_family != "interflo":
        return False

    # Check for special cases for specific families
    # Utile and Nextile walls should only match with specific bathtub families
    if wall_family in ["utile", "nextile"] and base_family not in ["nomad", "mackenzie", "exhibit", "new town", "rubix", "bosca", "cocoon", "corinthia"]:
        return False

    # Different brand checks
    if base_brand == "maax" and wall_brand != "maax":
        return False

    if base_brand == "neptune" and wall_brand != "neptune":
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
              or dictionaries with incompatibility reasons
    """
    results = []
    incompatibility_reasons = {}

    # Check for incompatibility reasons
    doors_cant_fit_reason = bathtub_info.get("Reason Doors Can't Fit")
    walls_cant_fit_reason = bathtub_info.get("Reason Walls Can't Fit")

    # If there are specific reasons why doors or walls can't fit, add them to the incompatibility reasons
    if pd.notna(doors_cant_fit_reason) and doors_cant_fit_reason:
        incompatibility_reasons["Tub Doors"] = doors_cant_fit_reason
        logger.info(f"Tub doors incompatibility reason found: {doors_cant_fit_reason}")

    if pd.notna(walls_cant_fit_reason) and walls_cant_fit_reason:
        incompatibility_reasons["Walls"] = walls_cant_fit_reason
        logger.info(f"Walls incompatibility reason found: {walls_cant_fit_reason}")

    # Check if necessary data exists
    if 'Tub Doors' not in data or 'Walls' not in data:
        logger.warning("Missing required sheets for bathtub compatibility")

        # Still add incompatibility reasons even if missing sheets
        for category, reason in incompatibility_reasons.items():
            results.append({
                "category": category,
                "reason": reason
            })
        return results

    tub_doors_df = data['Tub Doors']
    walls_df = data['Walls']
    tub_screens_df = data.get('Tub Screens', pd.DataFrame())

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
                series_compatible(tub_series, door_series, tub_brand, door.get("Brand"))
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
                    "image_url": image_handler.generate_image_url(door_data),
                    "product_page_url": door_data.get("Product Page URL", ""),
                    "nominal_dimensions": door_data.get("Nominal Dimensions", ""),
                    "brand": door_data.get("Brand", ""),
                    "series": door_data.get("Series", ""),
                    "glass_thickness": door_data.get("Glass Thickness", "") or door_data.get("Glass", ""),
                    "door_type": door_data.get("Door Type", "") or door_data.get("Door  Type", "") or door_data.get("Type", ""),
                    "max_door_width": door_data.get("Maximum Width", "")
                }
                compatible_doors.append(product_dict)
        except Exception as e:
            logger.error(f"Error processing tub door: {e}")

    # Find compatible tub screens using the same logic as tub doors
    # Only show screens if there are no door incompatibility reasons
    compatible_screens = []
    if not tub_screens_df.empty and "Tub Doors" not in incompatibility_reasons:
        for _, screen in tub_screens_df.iterrows():
            try:
                screen_fixed_panel_width = screen.get("Fixed Panel Width")
                screen_series = screen.get("Series")
                screen_id = str(screen.get("Unique ID", "")).strip()

                if not screen_id:
                    continue

                if (
                    tub_install == "Alcove" and
                    pd.notna(tub_width) and pd.notna(screen_fixed_panel_width) and
                    (tub_width - screen_fixed_panel_width) > 22 and
                    series_compatible(tub_series, screen_series, tub_brand, screen.get("Brand"))
                ):
                    # Format screen product data for the frontend
                    screen_data = screen.to_dict()
                    # Remove any NaN values
                    screen_data = {k: v for k, v in screen_data.items() if pd.notna(v)}

                    # Create a properly formatted product entry for the frontend
                    product_dict = {
                        "sku": screen_id,
                        "is_combo": False,
                        "_ranking": screen_data.get("Ranking", 999),
                        "name": screen_data.get("Product Name", ""),
                        "image_url": image_handler.generate_image_url(screen_data),
                        "product_page_url": screen_data.get("Product Page URL", ""),
                        "brand": screen_data.get("Brand", ""),
                        "series": screen_data.get("Series", ""),
                        "fixed_panel_width": screen_data.get("Fixed Panel Width", "")
                    }
                    compatible_screens.append(product_dict)
            except Exception as e:
                logger.error(f"Error processing tub screen: {e}")

    def find_closest_walls(tub_length, tub_width, candidate_walls):
        """
        Find walls with the closest dimensions to the tub based on combined distance.
        Only returns walls that are at least as large as the bathtub.
        """
        # First, filter out walls that are too small for the tub
        candidate_walls = candidate_walls.copy()

        # Only consider walls that are at least as large as the bathtub
        valid_walls = candidate_walls[(candidate_walls["Length"] >= tub_length) & 
                                      (candidate_walls["Width"] >= tub_width)]

        # If no valid walls found, return empty DataFrame
        if valid_walls.empty:
            logger.info(f"No walls found that are large enough for tub dimensions {tub_length} x {tub_width}")
            return valid_walls

        # Calculate distance metric for valid walls
        valid_walls["distance"] = (valid_walls["Length"] - tub_length).abs() + (valid_walls["Width"] - tub_width).abs()
        min_distance = valid_walls["distance"].min()

        # Return walls with minimum distance
        return valid_walls[valid_walls["distance"] == min_distance]

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
            "image_url": image_handler.generate_image_url(wall_data),
            "product_page_url": wall_data.get("Product Page URL", ""),
            "nominal_dimensions": wall_data.get("Nominal Dimensions", ""),
            "brand": wall_data.get("Brand", ""),
            "series": wall_data.get("Series", ""),
            "family": wall_data.get("Family", "")
        })

    # Step 2: Cut to Size walls (only closest size)
    # Only include walls that are large enough to fit the bathtub
    cut_walls_candidates = walls_df[
        (walls_df["Type"].str.lower().str.contains("tub", na=False)) &
        (walls_df["Cut to Size"] == "Yes") &
        (walls_df["Series"].apply(lambda x: series_compatible(tub_series, x))) &
        (walls_df.apply(lambda x: bathtub_brand_family_match(tub_brand, tub_family, x["Brand"], x["Family"]), axis=1)) &
        pd.notna(walls_df["Length"]) & pd.notna(walls_df["Width"]) &
        (walls_df["Length"] >= tub_length) & (walls_df["Width"] >= tub_width_actual)
    ].copy()

    logger.info(f"Found {len(cut_walls_candidates)} cut-to-size wall candidates")
    if not cut_walls_candidates.empty and pd.notna(tub_length) and pd.notna(tub_width_actual):
        # --- NEW: select closest cut-size wall(s) per family ---
        closest_cut_walls = pd.DataFrame()

        cut_walls_candidates["Family_norm"] = (
            cut_walls_candidates["Family"].astype(str).str.strip().str.lower()
        )

        for fam, fam_df in cut_walls_candidates.groupby("Family_norm"):
            fam_closest = find_closest_walls(tub_length, tub_width_actual, fam_df)
            closest_cut_walls = pd.concat([closest_cut_walls, fam_closest], ignore_index=True)

        for _, wall in closest_cut_walls.iterrows():
            wall_id = str(wall.get("Unique ID", "")).strip()
            logger.info(f"✅ Matched closest cut wall (family {wall.get('Family')}): {wall_id} - {wall.get('Product Name')}")
            wall_data = wall.to_dict()
            wall_data = {k: v for k, v in wall_data.items() if pd.notna(v)}
            compatible_walls.append({
                "sku": wall_id,
                "is_combo": False,
                "_ranking": wall_data.get("Ranking", 999),
                "name": wall_data.get("Product Name", ""),
                "image_url": image_handler.generate_image_url(wall_data),
                "product_page_url": wall_data.get("Product Page URL", ""),
                "nominal_dimensions": wall_data.get("Nominal Dimensions", ""),
                "brand": wall_data.get("Brand", ""),
                "series": wall_data.get("Series", ""),
                "family": wall_data.get("Family", "")
            })


    # Add incompatibility reasons to the results if they exist
    for category, reason in incompatibility_reasons.items():
        logger.info(f"Adding incompatibility reason for {category}: {reason}")
        results.append({
            "category": category,
            "reason": reason
        })

    # Only add compatible products for categories without incompatibility reasons
    if compatible_doors and "Tub Doors" not in incompatibility_reasons:
        # Sort the doors by ranking
        sorted_doors = sorted(compatible_doors, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Tub Doors", "products": sorted_doors})

    if compatible_screens and "Tub Doors" not in incompatibility_reasons:
        # Sort the screens by ranking
        sorted_screens = sorted(compatible_screens, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Tub Screens", "products": sorted_screens})

    if compatible_walls and "Walls" not in incompatibility_reasons:
        # Sort the walls by ranking
        sorted_walls = sorted(compatible_walls, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Walls", "products": sorted_walls})

    # Sort categories in the specified order
    category_order = [
        "Tub Doors",
        "Tub Screens", 
        "Walls"
    ]
    
    def get_category_priority(category_name):
        """Get the priority order for a category, with lower numbers appearing first"""
        try:
            return category_order.index(category_name)
        except ValueError:
            # If category not in predefined order, put it at the end
            return len(category_order)
    
    # Sort the results list by category priority
    results.sort(key=lambda x: get_category_priority(x.get("category", "")))

    return results