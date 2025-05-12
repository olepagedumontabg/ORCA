"""
Run the compatibility script with the correct Excel file
"""
import pandas as pd
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('compatibility_checker')

# File paths
excel_path = os.path.join('data', 'Product Data.xlsx')

# Make sure the Excel file exists
if not os.path.exists(excel_path):
    logger.error(f"Excel file not found: {excel_path}")
    sys.exit(1)

logger.info(f"Loading Excel file: {excel_path}")
excel_file = pd.ExcelFile(excel_path)

# Check for required sheets
required_sheets = ['Shower Bases', 'Shower Doors', 'Return Panels', 'Walls', 'Enclosures']
available_sheets = excel_file.sheet_names
logger.info(f"Available sheets: {available_sheets}")

missing_sheets = [sheet for sheet in required_sheets if sheet not in available_sheets]
if missing_sheets:
    logger.warning(f"Missing sheets: {missing_sheets}")
    # Try to find alternatives
    if 'Shower Doors' in missing_sheets and 'Doors' in available_sheets:
        logger.info("Using 'Doors' sheet instead of 'Shower Doors'")
        required_sheets.remove('Shower Doors')
        required_sheets.append('Doors')

# Create dataframe dictionary
dataframes = {}
for sheet in required_sheets:
    if sheet in available_sheets:
        dataframes[sheet] = excel_file.parse(sheet)
        logger.info(f"Loaded {sheet} with {len(dataframes[sheet])} rows")
    else:
        logger.warning(f"Sheet {sheet} not available, skipping")
        dataframes[sheet] = pd.DataFrame()  # Empty dataframe

# Define compatibility functions
def series_compatible(base_series, compare_series):
    if pd.isna(base_series) or pd.isna(compare_series):
        return False
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match_doors(base_brand, base_family, other_brand, other_family):
    if pd.isna(base_brand) or pd.isna(other_brand):
        return False
    return (
        (base_brand == "Maax" and other_brand == "Maax") or
        (base_brand == "Neptune" and other_brand == "Neptune") or
        (base_brand == "Aker" and other_brand == "Maax")
    )

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    if pd.isna(base_brand) or pd.isna(wall_brand):
        return False
    if pd.isna(base_family) or pd.isna(wall_family):
        return False
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

# Let's check if any sku is already in our database
from sqlalchemy import create_engine, text
import json
import os

def get_product_by_sku(sku, df, category="Shower Base"):
    # Check if the SKU exists in the given dataframe
    if 'Unique ID' not in df.columns:
        logger.warning(f"'Unique ID' column not found in dataframe")
        return None
        
    product = df[df['Unique ID'] == sku]
    if len(product) == 0:
        return None
        
    product_data = {
        'sku': sku,
        'category': category,
        'brand': product['Brand'].iloc[0] if 'Brand' in product.columns else None,
        'family': product['Family'].iloc[0] if 'Family' in product.columns else None,
        'series': product['Series'].iloc[0] if 'Series' in product.columns else None,
        'nominal_dimensions': product['Nominal Dimensions'].iloc[0] if 'Nominal Dimensions' in product.columns else None,
        'installation': product['Installation'].iloc[0] if 'Installation' in product.columns else None,
        'max_door_width': product['Max Door Width'].iloc[0] if 'Max Door Width' in product.columns else None,
        'width': product['Width'].iloc[0] if 'Width' in product.columns else None,
        'length': product['Length'].iloc[0] if 'Length' in product.columns else None,
        'height': product['Height'].iloc[0] if 'Height' in product.columns else None,
    }
    
    return product_data
    
# Check for a specific SKU
target_sku = '420043-541-001'
logger.info(f"Looking for SKU: {target_sku}")

if 'Shower Bases' in dataframes:
    product = get_product_by_sku(target_sku, dataframes['Shower Bases'])
    if product:
        logger.info(f"Found product: {json.dumps(product, indent=2)}")
        
        # Match compatibility
        logger.info("Finding compatible products...")
        
        # Get doors sheet
        door_sheet = 'Shower Doors' if 'Shower Doors' in dataframes else 'Doors'
        if door_sheet in dataframes:
            doors_df = dataframes[door_sheet]
            # Process doors
            matching_doors = []
            
            base_width = product.get("max_door_width")
            base_install = str(product.get("installation", "")).lower()
            base_series = product.get("series")
            base_fit_return = None  # Get from the dataframe if needed
            base_length = product.get("length")
            base_width_actual = product.get("width")
            base_nominal = product.get("nominal_dimensions")
            base_brand = product.get("brand")
            base_family = product.get("family")
            
            # Find matching doors
            for _, door in doors_df.iterrows():
                door_type = str(door.get("Type", "")).lower()
                door_min_width = door.get("Minimum Width")
                door_max_width = door.get("Maximum Width")
                door_has_return = door.get("Has Return Panel")
                door_family = door.get("Family")
                door_series = door.get("Series")
                door_brand = door.get("Brand")
                door_id = str(door.get("Unique ID", "")).strip()
                
                # Skip if required fields are missing
                if pd.isna(door_id) or not door_id:
                    continue
                    
                if (
                    "shower" in door_type and
                    "alcove" in base_install and
                    pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                    door_min_width <= base_width <= door_max_width and
                    series_compatible(base_series, door_series) and
                    brand_family_match_doors(base_brand, base_family, door_brand, door_family)
                ):
                    matching_doors.append({
                        'sku': door_id,
                        'requires_return': False,
                        'return_panel': None
                    })
                    logger.info(f"Found compatible door: {door_id}")
            
            if matching_doors:
                logger.info(f"Found {len(matching_doors)} compatible doors")
                
                # Add to database
                try:
                    DATABASE_URL = os.environ.get('DATABASE_URL')
                    if DATABASE_URL:
                        engine = create_engine(DATABASE_URL)
                        
                        # First clear existing compatibilities
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM compatibilities WHERE source_sku = :sku"), {'sku': target_sku})
                            conn.commit()
                            
                        # Insert new compatibilities
                        for door in matching_doors:
                            with engine.connect() as conn:
                                conn.execute(text("""
                                    INSERT INTO compatibilities 
                                    (source_sku, target_sku, target_category, requires_return_panel) 
                                    VALUES (:source, :target, :category, :return_panel)
                                """), {
                                    'source': target_sku,
                                    'target': door['sku'],
                                    'category': 'Doors',
                                    'return_panel': door['return_panel']
                                })
                                conn.commit()
                                logger.info(f"Added compatibility: {target_sku} -> {door['sku']} (Doors)")
                    else:
                        logger.error("DATABASE_URL not set, cannot update database")
                except Exception as e:
                    logger.error(f"Error updating database: {e}")
            else:
                logger.info("No compatible doors found")
        else:
            logger.warning(f"No doors sheet found, cannot find compatible doors")
        
        # Process walls
        if 'Walls' in dataframes:
            walls_df = dataframes['Walls']
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
                
                # Skip if required fields are missing
                if pd.isna(wall_id) or not wall_id:
                    continue
                
                wall_tolerance = 3  # inches
                
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
                
                if alcove_match or corner_match:
                    matching_walls.append({
                        'sku': wall_id,
                        'requires_return': False,
                        'return_panel': None
                    })
                    logger.info(f"Found compatible wall: {wall_id}")
            
            if matching_walls:
                logger.info(f"Found {len(matching_walls)} compatible walls")
                
                # Add to database
                try:
                    DATABASE_URL = os.environ.get('DATABASE_URL')
                    if DATABASE_URL:
                        engine = create_engine(DATABASE_URL)
                        
                        # Insert new compatibilities
                        for wall in matching_walls:
                            with engine.connect() as conn:
                                conn.execute(text("""
                                    INSERT INTO compatibilities 
                                    (source_sku, target_sku, target_category, requires_return_panel) 
                                    VALUES (:source, :target, :category, :return_panel)
                                """), {
                                    'source': target_sku,
                                    'target': wall['sku'],
                                    'category': 'Walls',
                                    'return_panel': wall['return_panel']
                                })
                                conn.commit()
                                logger.info(f"Added compatibility: {target_sku} -> {wall['sku']} (Walls)")
                    else:
                        logger.error("DATABASE_URL not set, cannot update database")
                except Exception as e:
                    logger.error(f"Error updating database: {e}")
            else:
                logger.info("No compatible walls found")
        else:
            logger.warning("No walls sheet found, cannot find compatible walls")
    else:
        logger.warning(f"SKU {target_sku} not found in Shower Bases")
else:
    logger.error("Shower Bases sheet not found in the Excel file")