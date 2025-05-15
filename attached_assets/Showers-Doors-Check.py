import pandas as pd
import logging

logger = logging.getLogger(__name__)

def series_compatible(base_series, compare_series):
    base_series = str(base_series).strip() if base_series else ""
    compare_series = str(compare_series).strip() if compare_series else ""

    if not base_series or not compare_series:
        return False
    if base_series.lower() == compare_series.lower():
        return True
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def find_showers_doors_compatibilities(data, shower_info):
    results = []

    if 'Doors' not in data:
        logger.warning("Missing Doors sheet")
        return results

    doors_df = data['Doors']
    shower_width = shower_info.get("Max Door Width")
    shower_height = shower_info.get("Max Door Height")
    shower_install = shower_info.get("Installation")
    shower_series = shower_info.get("Series")

    compatible_doors = []

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
            door_data = door.to_dict()
            door_data = {k: v for k, v in door_data.items() if pd.notna(v)}

            compatible_doors.append({
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
            })

    if compatible_doors:
        sorted_doors = sorted(compatible_doors, key=lambda x: x.get('_ranking', 999))
        results.append({"category": "Shower Doors", "products": sorted_doors})

    return results
