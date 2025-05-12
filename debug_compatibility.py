"""
Debug compatibility matching for specific SKU
"""
import os
import sys
import pandas as pd
import logging
import re  # Add regex support for dimension matching

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('compatibility_debug')

TARGET_SKU = '420043-541-001'

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
        
def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for walls compatibility"""
    if pd.isna(base_brand) or pd.isna(wall_brand):
        return False
    if pd.isna(base_family) or pd.isna(wall_family):
        return False
    
    # First check the brand combinations
    brand_match = (
        (base_brand == "Swan" and wall_brand == "Swan") or
        (base_brand == "Maax" and wall_brand == "Maax") or
        (base_brand == "Neptune" and wall_brand == "Neptune") or
        (base_brand == "Bootz" and wall_brand == "Bootz")
    )
    
    # Then check family combinations
    family_match = (
        (base_family == "W&B" and wall_family == "W&B") or
        (base_family == "Olio" and wall_family == "Olio") or
        (base_family == "Vellamo" and wall_brand == "Vellamo") or
        (base_family in ["B3", "B3Square", "Finesse", "Distinct", "Zone", "Olympia", "Icon"] and
         wall_family in ["Utile", "Denso", "Nextile", "Versaline"])
    )
    
    return brand_match or family_match

def main():
    # Find the Excel file
    excel_path = os.path.join('data', 'Product Data.xlsx')
    if not os.path.exists(excel_path):
        logger.error(f"Excel file not found: {excel_path}")
        sys.exit(1)
            
    logger.info(f"Loading Excel file: {excel_path}")
    
    # Load Excel file
    excel_file = pd.ExcelFile(excel_path)
    available_sheets = excel_file.sheet_names
    logger.info(f"Available sheets: {available_sheets}")
    
    # Load necessary sheets
    bases_df = excel_file.parse('Shower Bases')
    walls_df = excel_file.parse('Walls')
    
    # Find target SKU in shower bases
    base = bases_df[bases_df['Unique ID'] == TARGET_SKU]
    if len(base) == 0:
        logger.error(f"SKU {TARGET_SKU} not found in Shower Bases")
        sys.exit(1)
        
    # Get base info
    base_row = base.iloc[0]
    logger.info(f"Found SKU {TARGET_SKU}: {base_row.get('Product Name')}")
    
    # Get base properties
    base_width = base_row.get("Max Door Width")
    base_install = str(base_row.get("Installation", "")).lower()
    base_series = base_row.get("Series")
    base_fit_return = base_row.get("Fits Return Panel Size")
    base_length = base_row.get("Length")
    base_width_actual = base_row.get("Width")
    base_nominal = base_row.get("Nominal Dimensions")
    base_brand = base_row.get("Brand")
    base_family = base_row.get("Family")
    
    # Print all base properties for debugging
    logger.info(f"Base properties:")
    logger.info(f"  Width: {base_width_actual}")
    logger.info(f"  Length: {base_length}")
    logger.info(f"  Max Door Width: {base_width}")
    logger.info(f"  Installation: {base_install}")
    logger.info(f"  Series: {base_series}")
    logger.info(f"  Brand: {base_brand}")
    logger.info(f"  Family: {base_family}")
    logger.info(f"  Nominal Dimensions: {base_nominal}")
    
    # Set up tolerance
    wall_tolerance = 3  # inches for Walls
    
    # Test matching with each wall
    compatible_walls = []
    for _, wall in walls_df.iterrows():
        wall_sku = wall.get('Unique ID')
        if pd.isna(wall_sku) or not wall_sku:
            continue
            
        wall_type = str(wall.get("Type", "")).lower() if not pd.isna(wall.get("Type")) else ""
        wall_brand = wall.get("Brand")
        wall_series = wall.get("Series")
        wall_family = wall.get("Family")
        wall_nominal = wall.get("Nominal Dimensions")
        wall_length = wall.get("Length")
        wall_width = wall.get("Width")
        wall_cut = wall.get("Cut to Size")
        wall_name = wall.get("Product Name")
        
        # Skip if missing essential data
        if pd.isna(wall_brand) or pd.isna(wall_family) or pd.isna(wall_type):
            continue
            
        # Check for series compatibility
        series_match = series_compatible(base_series, wall_series)
        if not series_match:
            continue
            
        # Check for brand family match
        brand_match = brand_family_match_walls(base_brand, base_family, wall_brand, wall_family)
        # Log the brand/family details for easier debugging
        if base_brand == wall_brand:
            logger.debug(f"Brand match check: Base: {base_brand}/{base_family}, Wall: {wall_brand}/{wall_family}, Result: {brand_match}")
        if not brand_match:
            continue
            
        # For debugging, output all walls from the same brand
        if wall_brand == base_brand:
            logger.debug(f"Same brand wall: {wall_sku} - {wall_name} (Type: {wall_type})")
            
        # Check if this wall is for alcove shower
        alcove_suitable = "alcove shower" in wall_type
        if not alcove_suitable:
            continue
            
        # Check alcove compatibility since our base is alcove
        if base_install != "alcove" and base_install != "alcove or corner":
            continue
            
        # Log all alcove walls for Utile
        if "alcove shower" in wall_type and wall_family == "Utile":
            logger.debug(f"Potential wall: {wall_sku} - {wall_name}, Dimensions: {wall_nominal}")
            
        # Check nominal match (handle case-insensitive comparison and strip whitespace)
        base_nominal_clean = str(base_nominal).strip().lower() if pd.notna(base_nominal) else ""
        wall_nominal_clean = str(wall_nominal).strip().lower() if pd.notna(wall_nominal) else ""
        nominal_match = base_nominal_clean and wall_nominal_clean and base_nominal_clean == wall_nominal_clean
            
        # Also try comparing with various formats (e.g. "48 x 42" vs "48x42")
        if not nominal_match and base_nominal and wall_nominal:
            base_parts = re.sub(r'\s+', '', str(base_nominal)).split('x')
            wall_parts = re.sub(r'\s+', '', str(wall_nominal)).split('x')
            if len(base_parts) == 2 and len(wall_parts) == 2:
                try:
                    nominal_match = base_parts[0] == wall_parts[0] and base_parts[1] == wall_parts[1]
                except:
                    pass
            
        if nominal_match:
            logger.info(f"Nominal match: {wall_sku} - {wall_name} ({base_nominal} = {wall_nominal})")
            compatible_walls.append(wall_sku)
            continue
            
        # Check dimension match with tolerance
        if wall_cut == "Yes" and pd.notna(base_length) and pd.notna(wall_length) and pd.notna(base_width_actual) and pd.notna(wall_width):
            length_match = base_length <= wall_length and abs(base_length - wall_length) <= wall_tolerance
            width_match = base_width_actual <= wall_width and abs(base_width_actual - wall_width) <= wall_tolerance
            
            logger.debug(f"Checking dimensions: {wall_sku} - Length: {base_length} vs {wall_length}, Width: {base_width_actual} vs {wall_width}")
            
            if length_match and width_match:
                logger.info(f"Dimension match: {wall_sku} - {wall_name} (Base: {base_length}x{base_width_actual}, Wall: {wall_length}x{wall_width})")
                compatible_walls.append(wall_sku)
    
    # Show final results
    logger.info(f"Found {len(compatible_walls)} compatible walls:")
    for i, wall_sku in enumerate(compatible_walls):
        wall = walls_df[walls_df['Unique ID'] == wall_sku].iloc[0]
        logger.info(f"{i+1}. {wall_sku} - {wall.get('Product Name')} (Brand: {wall.get('Brand')}, Family: {wall.get('Family')})")
    
if __name__ == "__main__":
    main()