
import pandas as pd
import os

def match_compatibility():
    """
    Match shower bases with compatible doors and walls
    """
    # Set the workbook path to our environment
    workbook_path = os.path.join('data', 'test_base_doors.xlsx')
    
    # Load the Excel file
    excel_file = pd.ExcelFile(workbook_path)

    # Parse each sheet
    try:
        bases_df = excel_file.parse('Shower Bases')
    except:
        print("Error: 'Shower Bases' sheet not found")
        return
        
    try:
        doors_df = excel_file.parse('Shower Doors')
    except:
        print("Error: 'Shower Doors' sheet not found or renamed")
        try:
            doors_df = excel_file.parse('Doors')
            print("Found 'Doors' sheet instead")
        except:
            print("Error: Could not find any doors sheet")
            return
            
    try:
        return_panels_df = excel_file.parse('Return Panels')
    except:
        print("Warning: 'Return Panels' sheet not found")
        return_panels_df = pd.DataFrame()
        
    try:
        enclosures_df = excel_file.parse('Enclosures')
    except:
        print("Warning: 'Enclosures' sheet not found")
        enclosures_df = pd.DataFrame()
        
    try:
        walls_df = excel_file.parse('Walls')
    except:
        print("Warning: 'Walls' sheet not found")
        walls_df = pd.DataFrame()

    tolerance = 2  # inches
    wall_tolerance = 3  # inches for Walls

    if 'Compatible Doors' not in bases_df.columns:
        bases_df['Compatible Doors'] = ""
    else:
        bases_df['Compatible Doors'] = bases_df['Compatible Doors'].astype(str)

    if 'Compatible Walls' not in bases_df.columns:
        bases_df['Compatible Walls'] = ""
    else:
        bases_df['Compatible Walls'] = bases_df['Compatible Walls'].astype(str)

    for i, base in bases_df.iterrows():
        matching_values = []

        base_width = base.get("Max Door Width")
        base_install = str(base.get("Installation", "")).lower()
        base_series = base.get("Series")
        base_fit_return = base.get("Fits Return Panel Size")
        base_length = base.get("Length")
        base_width_actual = base.get("Width")
        base_nominal = base.get("Nominal Dimensions")
        base_brand = base.get("Brand")
        base_family = base.get("Family")

        # ---------- Doors ----------
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
                    matching_values.append(door_id)

            if (
                "shower" in door_type and
                "corner" in base_install and
                door_has_return == "Yes" and
                pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                door_min_width <= base_width <= door_max_width and
                series_compatible(base_series, door_series) and
                brand_family_match_doors(base_brand, base_family, door_brand, door_family)
            ):
                for _, panel in return_panels_df.iterrows():
                    panel_size = panel.get("Return Panel Size")
                    panel_family = panel.get("Family")
                    panel_brand = panel.get("Brand")
                    panel_id = str(panel.get("Unique ID", "")).strip()

                    if (
                        base_fit_return == panel_size and
                        brand_family_match_doors(base_brand, base_family, panel_brand, panel_family) and
                        door_id and panel_id
                    ):
                        matching_values.append(f"{door_id}|{panel_id}")

        # ---------- Enclosures ----------
        if "corner" in base_install:
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
                    matching_values.append(enc_id)

        # ---------- Walls ----------
        wall_matches = []
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
                wall_matches.append(wall_id)

        # ---------- Combine results ----------
        existing = str(base.get("Compatible Doors", "")).strip()
        if existing.lower() == "nan":
            existing = ""

        if matching_values:
            final_value = (
                existing + "|" + "|".join(matching_values)
                if existing and "|" not in existing
                else "|".join(matching_values)
            )
            bases_df.at[i, "Compatible Doors"] = final_value
        else:
            bases_df.at[i, "Compatible Doors"] = ""

        existing_walls = str(base.get("Compatible Walls", "")).strip()
        if existing_walls.lower() == "nan":
            existing_walls = ""

        if wall_matches:
            final_walls = (
                existing_walls + "|" + "|".join(wall_matches)
                if existing_walls and "|" not in existing_walls
                else "|".join(wall_matches)
            )
            bases_df.at[i, "Compatible Walls"] = final_walls
        else:
            bases_df.at[i, "Compatible Walls"] = ""

    with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        bases_df.to_excel(writer, sheet_name="Shower Bases", index=False)
        print(f"Updated {len(bases_df)} shower bases")

def series_compatible(base_series, compare_series):
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match_doors(base_brand, base_family, other_brand, other_family):
    return (
        (base_brand == "Maax" and other_brand == "Maax") or
        (base_brand == "Neptune" and other_brand == "Neptune") or
        (base_brand == "Aker" and other_brand == "Maax")
    )

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    return (
        (base_brand == "Swan" and wall_brand == "Swan") or
        (base_brand == "Maax" and wall_brand == "Maax") or
        (base_brand == "Neptune" and wall_brand == "Neptune") or
        (base_brand == "Bootz" and wall_brand == "Bootz") or
        (base_family == "W&B" and wall_family == "W&B") or
        (base_family == "Olio" and wall_family == "Olio") or
        (base_family == "Vellamo" and wall_brand == "Vellamo") or
        (base_family in ["B3", "Finesse", "Distinct", "Zone", "Olympia", "Icon"] and
         wall_family in ["Utile", "Denso", "Nextile", "Versaline"])
    )
