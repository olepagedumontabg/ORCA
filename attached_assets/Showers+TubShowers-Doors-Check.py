import pandas as pd

# Load the Excel file
workbook_path = 'test_base_doors.xlsx'  # Replace with your file path
excel_file = pd.ExcelFile(workbook_path)

showers_df = excel_file.parse('Showers')
tub_showers_df = excel_file.parse('Tub Showers')
doors_df = excel_file.parse('Doors')
tub_doors_df = excel_file.parse('Tub Doors')   # ✅ NEW

def series_compatible(base_series, compare_series):
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def match_showers_and_tub_showers():
    # ---------- Showers ----------
    if 'Compatible Doors' not in showers_df.columns:
        showers_df['Compatible Doors'] = ""
    else:
        showers_df['Compatible Doors'] = showers_df['Compatible Doors'].astype(str)

    for i, shower in showers_df.iterrows():
        matches = []
        shower_width = shower.get("Max Door Width")
        shower_height = shower.get("Max Door Height")
        shower_install = shower.get("Installation")
        shower_series = shower.get("Series")

        for _, door in doors_df.iterrows():
            door_type = str(door.get("Type", "")).lower()
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_max_height = door.get("Maximum Height")
            door_series = door.get("Series")
            door_id = str(door.get("Unique ID", "")).strip()

            if not door_id:
                continue

            if (
                "shower" in door_type and
                shower_install == "Alcove" and
                pd.notna(shower_width) and pd.notna(shower_height) and
                pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                door_min_width <= shower_width <= door_max_width and
                shower_height >= door_max_height and
                series_compatible(shower_series, door_series)
            ):
                matches.append(door_id)

        if matches:
            showers_df.at[i, "Compatible Doors"] = "|".join(matches)
        else:
            showers_df.at[i, "Compatible Doors"] = ""

    # ---------- Tub Showers ----------
    if 'Compatible Doors' not in tub_showers_df.columns:
        tub_showers_df['Compatible Doors'] = ""
    else:
        tub_showers_df['Compatible Doors'] = tub_showers_df['Compatible Doors'].astype(str)

    for i, tub in tub_showers_df.iterrows():
        matches = []
        tub_width = tub.get("Max Door Width")
        tub_height = tub.get("Max Door Height")
        tub_series = tub.get("Series")

        for _, door in tub_doors_df.iterrows():    # ✅ CHANGE: use Tub Doors
            door_min_width = door.get("Minimum Width")
            door_max_width = door.get("Maximum Width")
            door_max_height = door.get("Maximum Height")
            door_series = door.get("Series")
            door_id = str(door.get("Unique ID", "")).strip()

            if not door_id:
                continue

            if (
                pd.notna(tub_width) and pd.notna(tub_height) and
                pd.notna(door_min_width) and pd.notna(door_max_width) and pd.notna(door_max_height) and
                door_min_width <= tub_width <= door_max_width and
                tub_height >= door_max_height and
                series_compatible(tub_series, door_series)
            ):
                matches.append(door_id)

        if matches:
            tub_showers_df.at[i, "Compatible Doors"] = "|".join(matches)
        else:
            tub_showers_df.at[i, "Compatible Doors"] = ""

    # ---------- Save ----------
    with pd.ExcelWriter(workbook_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        showers_df.to_excel(writer, sheet_name="Showers", index=False)
        tub_showers_df.to_excel(writer, sheet_name="Tub Showers", index=False)

match_showers_and_tub_showers()
