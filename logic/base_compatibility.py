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
        list: List of dictionaries containing category and compatible SKUs,
              or dictionaries with incompatibility reasons
    """
    try:
        compatible_products = []
        incompatibility_reasons = {}

        # Debug: Check what type of object base_info is
        logger.debug(f"base_info type: {type(base_info)}")
        logger.debug(f"base_info content: {base_info}")
        
        if not isinstance(base_info, dict):
            logger.error(f"Expected dict for base_info, got {type(base_info)}: {base_info}")
            return []

        # Check for incompatibility reasons
        doors_cant_fit_reason = base_info.get("Reason Doors Can't Fit")
        walls_cant_fit_reason = base_info.get("Reason Walls Can't Fit")

        # If there are specific reasons why doors or walls can't fit, add them to the incompatibility reasons
        if pd.notna(doors_cant_fit_reason) and doors_cant_fit_reason:
            incompatibility_reasons["Shower Doors"] = doors_cant_fit_reason
            logger.info(f"Shower doors incompatibility reason found: {doors_cant_fit_reason}")

        if pd.notna(walls_cant_fit_reason) and walls_cant_fit_reason:
            incompatibility_reasons["Walls"] = walls_cant_fit_reason
            logger.info(f"Walls incompatibility reason found: {walls_cant_fit_reason}")

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
            logger.debug(f"Doors incompatibility reason found: {doors_cant_fit_reason}")
            
        if pd.notna(walls_cant_fit_reason) and walls_cant_fit_reason:
            incompatibility_reasons["Walls"] = walls_cant_fit_reason
            logger.debug(f"Walls incompatibility reason found: {walls_cant_fit_reason}")
        else:
            logger.debug(f"No walls incompatibility reason - walls processing will continue")

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
        alcove_doors = []
        corner_doors = []
        matching_walls = []
        matching_screens = []
        matching_enclosures = []

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
                    and series_compatible(base_series, door_series, base_info.get("Brand"), door_brand))

                logger.debug(f"    Alcove match: {alcove_match}")
                logger.debug(
                    f"    Door width range: {door_min_width} <= {base_width} <= {door_max_width}: {door_min_width <= base_width <= door_max_width if pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) else 'Cannot compare'}"
                )
                logger.debug(
                    f"    Series match: {series_compatible(base_series, door_series, base_info.get('Brand'), door_brand)}"
                )

                if alcove_match:
                    if door_id:
                        # Create product dictionary with all required fields
                        door_product = {
                            "sku": door_id,
                            "name": door.get("Product Name", ""),
                            "brand": door.get("Brand", ""),
                            "series": door.get("Series", ""),
                            "category": "Shower Doors",
                            "glass_thickness": door.get("Glass Thickness", ""),
                            "door_type": door.get("Door Type", ""),
                            "image_url": door.get("Image URL", ""),
                            "product_page_url": door.get("Product Page URL", ""),
                            "_ranking": door.get("Ranking", 999),
                            "is_combo": False
                        }
                        # Check if base supports both alcove and corner - if so, separate them
                        if "alcove" in base_install and "corner" in base_install:
                            alcove_doors.append(door_product)
                            logger.debug(f"    ✓ Added door {door_id} to alcove doors")
                        else:
                            matching_doors.append(door_product)
                            logger.debug(f"    ✓ Added door {door_id} to matching doors")

                # Corner installation match with return panel
                # Check if door can work with corner bases - either has explicit return panel support
                # or is compatible based on width dimensions for corner installations
                has_return_panel = door_has_return == "Yes"
                corner_door_compatible = (
                    "corner" in base_install 
                    and pd.notna(base_width) and pd.notna(door_min_width)
                    and pd.notna(door_max_width)
                    and door_min_width <= base_width <= door_max_width
                    and series_compatible(base_series, door_series, base_info.get("Brand"), door_brand))
                
                corner_match = corner_door_compatible

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
                            # Primary matching: exact return panel size match
                            exact_panel_match = (pd.notna(base_fit_return)
                                                 and pd.notna(panel_size)
                                                 and base_fit_return == panel_size
                                                 and door_family == panel_family
                                                 and door_id and panel_id)
                            
                            # Fallback matching: for corner bases without return panel size info
                            # For pure corner bases, be very flexible with family matching
                            # This allows corner doors to work with any compatible return panel
                            is_pure_corner = "corner" in base_install and "alcove" not in base_install
                            
                            if is_pure_corner:
                                # For pure corner bases, allow any family combination
                                family_compatible = True
                            else:
                                # For mixed bases, use stricter family matching
                                family_compatible = door_family == panel_family
                            
                            fallback_panel_match = (not pd.notna(base_fit_return)
                                                   and "corner" in base_install
                                                   and family_compatible
                                                   and door_id and panel_id)
                            
                            panel_match = exact_panel_match or fallback_panel_match

                            logger.debug(f"      Panel match: {panel_match}")
                            logger.debug(f"        Door family: '{door_family}', Panel family: '{panel_family}'")
                            logger.debug(f"        Exact match: {exact_panel_match}, Fallback match: {fallback_panel_match}")
                            logger.debug(f"        Is pure corner: {is_pure_corner}, Family compatible: {family_compatible}")
                            logger.debug(
                                f"      Base fits return panel size: {base_fit_return} == {panel_size}: {base_fit_return == panel_size if pd.notna(base_fit_return) and pd.notna(panel_size) else 'Cannot compare'}"
                            )
                            logger.debug(
                                f"      Door family match: {door_family} == {panel_family}: {door_family == panel_family if door_family and panel_family else 'Cannot compare'}"
                            )

                            if panel_match:
                                combo_id = f"{door_id}|{panel_id}"
                                # Create combo product dictionary with main_product structure
                                combo_product = {
                                    "sku": combo_id,
                                    "is_combo": True,
                                    "_ranking": door.get("Ranking", 999),
                                    "main_product": {
                                        "sku": door_id,
                                        "name": door.get("Product Name", ""),
                                        "brand": door.get("Brand", ""),
                                        "series": door.get("Series", ""),
                                        "glass_thickness": door.get("Glass Thickness", ""),
                                        "door_type": door.get("Door Type", ""),
                                        "image_url": door.get("Image URL", ""),
                                        "product_page_url": door.get("Product Page URL", ""),
                                        "nominal_dimensions": door.get("Nominal Dimensions", ""),
                                        "max_door_width": door.get("Maximum Width", ""),
                                        "material": door.get("Material", "")
                                    },
                                    "secondary_product": {
                                        "sku": panel_id,
                                        "name": panel.get("Product Name", ""),
                                        "brand": panel.get("Brand", ""),
                                        "series": panel.get("Series", ""),
                                        "image_url": panel.get("Image URL", ""),
                                        "product_page_url": panel.get("Product Page URL", "")
                                    }
                                }
                                # For corner-compatible doors, add to corner_doors array
                                if "corner" in base_install:
                                    corner_doors.append(combo_product)
                                    logger.debug(f"      ✓ Added combo product {combo_id} to corner doors")
                                else:
                                    matching_doors.append(combo_product)
                                    logger.debug(f"      ✓ Added combo product {combo_id} to matching doors")

        # ---------- Enclosures ----------
        if 'Enclosures' in data and "corner" in base_install:
            enclosures_df = data['Enclosures']
            logger.debug(
                f"Checking compatibility with {len(enclosures_df)} enclosures")

            for _, enclosure in enclosures_df.iterrows():
                enc_series = enclosure.get("Series")
                enc_brand = enclosure.get("Brand")
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

                series_match = series_compatible(base_series, enc_series, base_info.get("Brand"), enc_brand)
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
                    # Create enclosure product dictionary
                    enclosure_product = {
                        "sku": enc_id,
                        "name": enclosure.get("Product Name", ""),
                        "brand": enclosure.get("Brand", ""),
                        "series": enclosure.get("Series", ""),
                        "category": "Enclosures",
                        "glass_thickness": enclosure.get("Glass Thickness", ""),
                        "door_type": enclosure.get("Door Type", ""),
                        "image_url": enclosure.get("Image URL", ""),
                        "product_page_url": enclosure.get("Product Page URL", ""),
                        "_ranking": enclosure.get("Ranking", 999),
                        "is_combo": False
                    }
                    matching_enclosures.append(enclosure_product)
                    logger.debug(
                        f"    ✓ Added enclosure {enc_id} to matching enclosures")

        # ---------- Shower Screens ----------
        if 'Shower Screens' in data:
            screens_df = data['Shower Screens']
            logger.debug(f"Processing {len(screens_df)} shower screens for compatibility")
            
            for _, screen in screens_df.iterrows():
                screen_id = str(screen.get("Unique ID", "")).strip()
                screen_name = screen.get("Product Name", "")
                screen_fixed_panel_width = screen.get("Fixed Panel Width")
                screen_brand = screen.get("Brand")
                screen_series = screen.get("Series")
                
                logger.debug(f"  Checking screen: {screen_id} - {screen_name}")
                logger.debug(f"    Fixed Panel Width: {screen_fixed_panel_width}")
                logger.debug(f"    Base Max Door Width: {base_width}")
                
                # Check if we have valid numeric values for both measurements
                if pd.notna(base_width) and pd.notna(screen_fixed_panel_width):
                    try:
                        base_width_num = float(base_width)
                        screen_width_num = float(screen_fixed_panel_width)
                        width_difference = base_width_num - screen_width_num
                        
                        logger.debug(f"    Width difference: {base_width_num} - {screen_width_num} = {width_difference}")
                        
                        # Check compatibility: Max Door Width - Fixed Panel Width > 22
                        # Compatible with both Alcove and Corner bases
                        screen_compatible = (
                            width_difference > 22 and
                            series_compatible(base_series, screen_series, base_info.get("Brand"), screen_brand) and
                            ("alcove" in base_install or "corner" in base_install)
                        )
                        
                        logger.debug(f"    Screen compatible: {screen_compatible}")
                        logger.debug(f"    Series match: {series_compatible(base_series, screen_series, base_info.get('Brand'), screen_brand)}")
                        logger.debug(f"    Installation type valid: {'alcove' in base_install or 'corner' in base_install}")
                        
                        if screen_compatible and screen_id:
                            screen_product = {
                                "sku": screen_id,
                                "name": screen.get("Product Name", ""),
                                "brand": screen.get("Brand", ""),
                                "series": screen.get("Series", ""),
                                "category": "Shower Screens",
                                "image_url": screen.get("Image URL", ""),
                                "product_page_url": screen.get("Product Page URL", ""),
                                "_ranking": screen.get("Ranking", 999),
                                "is_combo": False,
                                "fixed_panel_width": screen_fixed_panel_width
                            }
                            matching_screens.append(screen_product)
                            logger.debug(f"    ✓ Added screen {screen_id} to matching screens")
                    
                    except (ValueError, TypeError) as e:
                        logger.debug(f"    Error converting measurements to numbers: {e}")
                        continue
                else:
                    logger.debug(f"    Missing required measurements - skipping")

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
                wall_name = wall.get("Product Name", "")

                if not wall_id:
                    continue

                alcove_match = (
                    "alcove shower" in wall_type
                    and (base_install in ["alcove", "alcove or corner"])
                    and series_compatible(base_series, wall_series, base_info.get("Brand"), wall_brand)
                    and brand_family_match(base_brand, base_family, wall_brand,
                                           wall_family))

                corner_match = (
                    "corner shower" in wall_type
                    and (base_install in ["corner", "alcove or corner"])
                    and series_compatible(base_series, wall_series, base_info.get("Brand"), wall_brand)
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
                        "id":      wall_id,
                        "family":  str(wall_family).strip().lower(),
                        "length":  wall_length,
                        "width":   wall_width
                    })
                


            # ✅ Select closest cut size walls
            closest_cut_ids = []
            if cut_candidates:
                from collections import defaultdict

                by_family = defaultdict(list)
                for c in cut_candidates:
                    by_family[c["family"]].append(c)

                for fam, lst in by_family.items():
                    min_len = min(c["length"] for c in lst)
                    min_w   = min(
                        c["width"] for c in lst if c["length"] == min_len
                    )
                    closest_cut_ids.extend(
                        c["id"]
                        for c in lst
                        if c["length"] == min_len and c["width"] == min_w
                    )

            # ✅ Add all matches - convert IDs to product dictionaries
            all_wall_ids = nominal_matches + closest_cut_ids
            
            for wall_id in all_wall_ids:
                # Convert wall_id to match the DataFrame type (likely int)
                try:
                    wall_id_lookup = int(wall_id) if isinstance(wall_id, str) else wall_id
                except (ValueError, TypeError):
                    wall_id_lookup = wall_id
                
                # Find the wall data for this ID - handle both string and numeric comparisons
                wall_row = walls_df[
                    (walls_df['Unique ID'] == wall_id_lookup) | 
                    (walls_df['Unique ID'].astype(str) == str(wall_id_lookup))
                ]
                if not wall_row.empty:
                    wall = wall_row.iloc[0]
                    wall_product = {
                        "sku": wall_id,
                        "name": wall.get("Product Name", ""),
                        "brand": wall.get("Brand", ""),
                        "series": wall.get("Series", ""),
                        "category": "Walls",
                        "image_url": wall.get("Image URL", ""),
                        "product_page_url": wall.get("Product Page URL", ""),
                        "_ranking": wall.get("Ranking", 999),
                        "is_combo": False,
                        "material": wall.get("Material", "")
                    }
                    matching_walls.append(wall_product)

        # Add incompatibility reasons to the results if they exist
        for category, reason in incompatibility_reasons.items():
            compatible_products.append({
                "category": category,
                "reason": reason
            })
        
        # Only add compatible products for categories without incompatibility reasons
        if "Shower Doors" not in incompatibility_reasons:
            # Check if base supports both alcove and corner installations
            supports_both = "alcove" in base_install and "corner" in base_install
            is_corner_only = "corner" in base_install and "alcove" not in base_install
            
            # Organize doors by type based on base installation type
            if alcove_doors or corner_doors:
                # Split mode: separate categories with installation-specific names
                if alcove_doors:
                    sorted_alcove_doors = sorted(alcove_doors, key=lambda x: x.get('_ranking', 999))
                    logger.debug(f"Adding {len(sorted_alcove_doors)} alcove doors to results")
                    if supports_both:
                        compatible_products.append({"category": "Doors for Alcove Installation", "products": sorted_alcove_doors})
                    else:
                        compatible_products.append({"category": "Alcove Doors", "products": sorted_alcove_doors})
                
                if corner_doors:
                    sorted_corner_doors = sorted(corner_doors, key=lambda x: x.get('_ranking', 999))
                    logger.debug(f"Adding {len(sorted_corner_doors)} corner doors to results")
                    if supports_both:
                        compatible_products.append({"category": "Doors + Return Panels for Corner Installation", "products": sorted_corner_doors})
                    elif is_corner_only:
                        compatible_products.append({"category": "Doors + Return Panels", "products": sorted_corner_doors})
                    else:
                        compatible_products.append({"category": "Corner Doors", "products": sorted_corner_doors})
            elif matching_doors:
                # Regular mode: single category for all doors
                sorted_doors = sorted(matching_doors, key=lambda x: x.get('_ranking', 999))
                logger.debug(f"Adding {len(sorted_doors)} shower doors to results")
                for door in sorted_doors[:3]:  # Log first few doors
                    logger.debug(f"  Door: {door.get('sku')} - {door.get('name')} (combo: {door.get('is_combo', False)})")
                compatible_products.append({"category": "Shower Doors", "products": sorted_doors})

        if matching_screens:
            # Sort the screens by ranking
            sorted_screens = sorted(matching_screens, key=lambda x: x.get('_ranking', 999))
            logger.debug(f"Adding {len(sorted_screens)} shower screens to results")
            for screen in sorted_screens[:3]:  # Log first few screens
                logger.debug(f"  Screen: {screen.get('sku')} - {screen.get('name')}")
            compatible_products.append({"category": "Shower Screens", "products": sorted_screens})

        if matching_walls and "Walls" not in incompatibility_reasons:
            # Sort the walls by ranking
            sorted_walls = sorted(matching_walls, key=lambda x: x.get('_ranking', 999))
            logger.debug(f"Adding {len(sorted_walls)} walls to results")
            for wall in sorted_walls[:3]:  # Log first few walls
                logger.debug(f"  Wall: {wall.get('sku')} - {wall.get('name')}")
            compatible_products.append({"category": "Walls", "products": sorted_walls})
        else:
            logger.debug(f"Walls not added: matching_walls={len(matching_walls) if matching_walls else 0}, incompatibility={incompatibility_reasons.get('Walls', 'None')}")

        if matching_enclosures:
            # Check if base supports both alcove and corner installations
            supports_both = "alcove" in base_install and "corner" in base_install
            is_corner_only = "corner" in base_install and "alcove" not in base_install
            
            # Sort the enclosures by ranking
            sorted_enclosures = sorted(matching_enclosures, key=lambda x: x.get('_ranking', 999))
            logger.debug(f"Adding {len(sorted_enclosures)} enclosures to results")
            for enclosure in sorted_enclosures[:3]:  # Log first few enclosures
                logger.debug(f"  Enclosure: {enclosure.get('sku')} - {enclosure.get('name')}")
            
            # Use appropriate category name based on installation type
            if supports_both:
                category_name = "Enclosures for Corner Installation"
            elif is_corner_only:
                category_name = "Enclosures"
            else:
                category_name = "Enclosures"
                
            compatible_products.append({"category": category_name, "products": sorted_enclosures})

        logger.debug(f"Final results summary:")
        logger.debug(f"  Doors found: {len(matching_doors)} (regular), {len(alcove_doors)} (alcove), {len(corner_doors)} (corner)")
        logger.debug(f"  Screens found: {len(matching_screens)}")
        logger.debug(f"  Walls found: {len(matching_walls)}")
        logger.debug(f"  Enclosures found: {len(matching_enclosures)}")
        logger.debug(f"  Incompatibility reasons: {incompatibility_reasons}")
        logger.debug(f"  Compatible products returned: {len(compatible_products)}")

        return compatible_products

    except Exception as e:
        import traceback
        logger.error(f"Error in find_base_compatibilities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


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

    # Universal compatibility: Dreamline and Swan are compatible with any series
    if compare_brand in ["dreamline", "swan"] or base_brand in ["dreamline", "swan"]:
        return True

    # If either series is empty, they're compatible (relaxed rule for cross-brand compatibility)
    if not base_series or not compare_series:
        return True

    # Same series are always compatible
    if base_series.lower() == compare_series.lower():
        return True

    # Galerie compatibility rules
    if base_series == "Galerie":
        return compare_series in ["Galerie", "Neptune"]
    
    # Entrepreneur compatibility rules
    if base_series == "Entrepreneur":
        return compare_series in ["Entrepreneur", "Neptune"]
    
    # Neptune compatibility rules
    if base_series == "Neptune":
        return compare_series in ["Galerie", "Neptune", "Entrepreneur"]
    
    # Special case for Retail compatibility
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    
    # MAAX compatibility rules
    if base_series == "MAAX":
        return compare_series in [
            "Retail", "MAAX", "Collection", "Professional"]
    
    # Collection and Professional compatibility
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    
    # Default case - no other compatibility
    return False


def brand_family_match(base_brand, base_family, wall_brand, wall_family):
    """
    Check if base brand/family matches wall brand/family based on specific business rules.

    Args:
        base_brand (str): Brand of the base product
        base_family (str): Family of the base product
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

    if base_family == "vellamo" and wall_family != "vellamo":
        return False

    if wall_family == "vellamo" and base_family != "vellamo":
        return False

    if base_family == "interflo" and wall_family != "interflo":
        return False

    if wall_family == "interflo" and base_family != "interflo":
        return False

    # Check for special cases for specific families
    if base_family == "w&b" and wall_family != "w&b":
        return False

    if wall_family == "w&b" and base_family != "w&b":
        return False

    # Special family compatibility rules
    # Utile and Nextile walls should only match with specific base families
    if wall_family in ["utile", "nextile"] and base_family not in ["b3", "finesse", "distinct", "zone", "olympia", "icon", "roka"]:
        return False

    # Different brand checks
    if base_brand == "maax" and wall_brand != "maax":
        return False

    if base_brand == "bootz" and wall_brand != "bootz":
        return False

    # If we passed all restrictions and brands match, we're compatible
    if base_brand == wall_brand:
        return True

    # Default case - no match
    return False
