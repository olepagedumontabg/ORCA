"""
Load a single SKU and its compatibilities for testing
"""
import pandas as pd
import os
import sys
import logging
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('single_sku_loader')

# Target SKU to process
TARGET_SKU = '420043-541-001'

def main():
    # Database connection
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
        
    # Find the Excel file
    excel_path = os.path.join('data', 'Product Data.xlsx')
    if not os.path.exists(excel_path):
        logger.error(f"Excel file not found: {excel_path}")
        sys.exit(1)
        
    logger.info(f"Loading Excel file: {excel_path}")
    excel_file = pd.ExcelFile(excel_path)
    
    # Get list of available sheets
    sheets = excel_file.sheet_names
    logger.info(f"Available sheets: {sheets}")
    
    # Load relevant sheets
    bases_df = excel_file.parse('Shower Bases')
    doors_df = excel_file.parse('Shower Doors') if 'Shower Doors' in sheets else excel_file.parse('Doors')
    walls_df = excel_file.parse('Walls') if 'Walls' in sheets else pd.DataFrame()
    
    # Find our target SKU
    logger.info(f"Looking for SKU: {TARGET_SKU}")
    base = bases_df[bases_df['Unique ID'] == TARGET_SKU]
    if len(base) == 0:
        logger.error(f"SKU {TARGET_SKU} not found in Shower Bases")
        sys.exit(1)
        
    logger.info(f"Found SKU {TARGET_SKU}: {base['Product Name'].iloc[0]}")
    
    # Get base properties
    base_width = base["Max Door Width"].iloc[0]
    base_install = str(base["Installation"].iloc[0]).lower()
    base_series = base["Series"].iloc[0]
    base_brand = base["Brand"].iloc[0]
    base_family = base["Family"].iloc[0]
    
    logger.info(f"Base properties: Installation={base_install}, Max Width={base_width}, Series={base_series}, Brand={base_brand}, Family={base_family}")
    
    # Find compatible doors
    compatible_doors = []
    for _, door in doors_df.iterrows():
        door_sku = door.get('Unique ID')
        if pd.isna(door_sku) or not door_sku:
            continue
            
        door_type = str(door.get("Type", "")).lower() if not pd.isna(door.get("Type")) else ""
        door_min_width = door.get("Minimum Width")
        door_max_width = door.get("Maximum Width")
        door_family = door.get("Family")
        door_series = door.get("Series")
        door_brand = door.get("Brand")
        
        # Skip if required fields are missing
        if pd.isna(door_min_width) or pd.isna(door_max_width):
            continue
        
        # Make sure data is valid for comparison
        if not pd.notna(door_min_width) or not pd.notna(door_max_width) or not pd.notna(base_width):
            logger.warning(f"Skipping door {door_sku} due to invalid dimensions data")
            continue
            
        try:
            # Match based on compatibility logic - handle NaN and invalid data safely
            if "shower" in door_type and "alcove" in base_install:
                if door_min_width <= base_width <= door_max_width:
                    if series_compatible(base_series, door_series) and brand_family_match(base_brand, base_family, door_brand, door_family):
                        compatible_doors.append(door_sku)
                        logger.info(f"Compatible door: {door_sku} - {door.get('Product Name')}")
        except Exception as e:
            logger.warning(f"Error matching door {door_sku}: {e}")
    
    # Find compatible walls
    compatible_walls = []
    for _, wall in walls_df.iterrows():
        wall_sku = wall.get('Unique ID')
        if pd.isna(wall_sku) or not wall_sku:
            continue
            
        wall_type = str(wall.get("Type", "")).lower()
        wall_brand = wall.get("Brand")
        wall_series = wall.get("Series")
        wall_family = wall.get("Family")
        
        # Match based on your compatibility logic
        is_compatible = (
            "alcove shower" in wall_type and
            (base_install in ["alcove", "alcove or corner"]) and
            series_compatible(base_series, wall_series) and
            brand_family_match_walls(base_brand, base_family, wall_brand, wall_family)
        )
        
        if is_compatible:
            compatible_walls.append(wall_sku)
            logger.info(f"Compatible wall: {wall_sku} - {wall.get('Product Name')}")
    
    # Clear existing data and store in database
    engine = create_engine(db_url)
    
    try:
        # Clear existing compatibility data for this base
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM compatibilities WHERE source_sku = :sku"), {'sku': TARGET_SKU})
            conn.commit()
            logger.info(f"Cleared existing compatibility data for {TARGET_SKU}")
        
        # Store door compatibilities
        for door_sku in compatible_doors:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO compatibilities 
                    (source_sku, target_sku, target_category, requires_return_panel) 
                    VALUES (:source, :target, :category, :return_panel)
                """), {
                    'source': TARGET_SKU,
                    'target': door_sku,
                    'category': 'Doors',
                    'return_panel': None
                })
                conn.commit()
                logger.info(f"Added door compatibility: {door_sku}")
        
        # Store wall compatibilities
        for wall_sku in compatible_walls:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO compatibilities 
                    (source_sku, target_sku, target_category, requires_return_panel) 
                    VALUES (:source, :target, :category, :return_panel)
                """), {
                    'source': TARGET_SKU,
                    'target': wall_sku,
                    'category': 'Walls',
                    'return_panel': None
                })
                conn.commit()
                logger.info(f"Added wall compatibility: {wall_sku}")
        
        logger.info(f"Successfully stored {len(compatible_doors)} door and {len(compatible_walls)} wall compatibilities")
        
    except Exception as e:
        logger.error(f"Error storing compatibilities: {e}")

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    if pd.isna(base_series) or pd.isna(compare_series):
        return False
        
    if base_series == "Retail":
        return compare_series in ["Retail", "MAAX"]
    if base_series == "MAAX":
        return compare_series in ["Retail", "MAAX", "Collection", "Professional"]
    if base_series in ["Collection", "Professional"]:
        return compare_series in ["MAAX", "Collection", "Professional"]
    return False

def brand_family_match(base_brand, base_family, other_brand, other_family):
    """Check if brands and families match for doors compatibility"""
    if pd.isna(base_brand) or pd.isna(other_brand):
        return False
        
    return (
        (base_brand == "Maax" and other_brand == "Maax") or
        (base_brand == "Neptune" and other_brand == "Neptune") or
        (base_brand == "Aker" and other_brand == "Maax")
    )

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for walls compatibility"""
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

if __name__ == "__main__":
    main()