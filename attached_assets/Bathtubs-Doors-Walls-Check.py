import pandas as pd

# Load Excel file
workbook_path = 'Product Data_05_12_2025.xlsx'  # Replace with your file path
excel_file = pd.ExcelFile(workbook_path)

bathtubs_df = excel_file.parse('Bathtubs')
tub_doors_df = excel_file.parse('Tub Doors')
walls_df = excel_file.parse('Walls')

def series_compatible(base_series, compare_series):
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def bathtub_brand_family_match(base_brand, base_family, wall_brand, wall_family):
    base_brand = str(base_brand).strip().lower()
    base_family = str(base_family).strip().lower()
    wall_brand = str(wall_brand).strip().lower()
    wall_family = str(wall_family).strip().lower()

    # Maax restriction
    if base_brand == "maax" and wall_brand != "maax":
        return False

    return (
        (base_brand == "swan" and wall_brand == "swan") or
        (base_brand == "bootz" and wall_brand == "bootz") or
        (base_family == "olio" and wall_family == "olio") or
        (base_family == "vellamo" and wall_brand == "vellamo") or
        (base_family in ["nomad", "mackenzie", "exhibit", "new town", "rubix", "bosca", "cocoon", "corinthia"] and
         wall_family in ["utile", "nextile", "versaline"])
    )

def match_bathtubs_doors_and_walls():
    tolerance = 3  # inches

    if 'Compatible Doors' not in bathtubs_df.columns:
        bathtubs_df['Compatible Doors'] = ""
    else:
        bathtubs_df['Compatible Doors'] = bathtubs_df['Compatible Doors'].astype(str)

    if 'Compatible Walls' not in bathtubs_df.columns:
        bathtubs_df['Compatible Walls'] = ""
    else:
        bathtubs_df['Compatible Walls'] = bathtubs_df['Compatible Walls'].astype(str)

    for i, tub in bathtubs_df.iterrows():
        door_matches = []
        wall_matches = []

        tub_width = tub.get("Max Door Width")
        tub_install = tub.get("Installation")
        tub_series = tub.get("Series")
        tub_brand = tub.get("Brand")
        tub_family = tub.get("Family")
        tub_nominal = tub.get("Nominal Dimensions")
        tub_length = tub.get("Length")
        tub_width_actual = tub.get("Width")

        # ---------- Doors ----------
        for _, door in tub_doors_df.iterrows():
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
                door_matches.append(door_id)

        # ---------- Walls ----------
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

            if (
                "tub" in wall_type and
                series_compatible(tub_series, wall_series) and
                bathtub_brand_family_match(tub_brand, tub_family, wall_brand, wall_family) and
                (
                    tub_nominal == wall_nominal or
                    (wall_cut == "Yes" and
                     pd.notna(tub_length) and pd.notna(wall_length) and
                     pd.notna(tub_width_actual) and pd.notna(wall_width) and
                     tub_length >= wall_length - tolerance and
                     tub_length <= wall_length + tolerance and
                     tub_width_actual >= wall_width - tolerance and
                     tub_width_actual <= wall_width + tolerance)
                )
            ):
                wall_matches.append(wall_id)

        # ---------- Set Compatible Doors ----------
        if door_matches:
            bathtubs_df.at[i, "Compatible Doors"] = "|".join(door_matches)
        else:
            bathtubs_df.at[i, "Compatible Doors"] = ""

        # ---------- Set Compatible Walls ----------
        if wall_matches:
            bathtubs_df.at[i, "Compatible Walls"] = "|".join(wall_matches)
        else:
            bathtubs_df.at[i, "Compatible Walls"] = ""

    # ---------- Save back ----------
    with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        bathtubs_df.to_excel(writer, sheet_name="Bathtubs", index=False)

match_bathtubs_doors_and_walls()
