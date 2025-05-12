"""
Import and Process Script
A streamlined script to import product data and calculate compatibilities.
"""
import os
import sys
import logging
import pandas as pd
import json
from sqlalchemy import create_engine, text
from main import app, db
from models import Product, Compatibility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('import_processor')

def load_excel_files():
    """Load all Excel files from the data directory"""
    data = {}
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data')
        logger.info(f"Loading Excel files from: {data_path}")
        
        # We'll just use the first Excel file (Product Data.xlsx) to avoid duplicates
        file_path = os.path.join(data_path, 'Product Data.xlsx')
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return data
        
        # Get list of sheet names
        excel_file = pd.ExcelFile(file_path)
        
        # Load each sheet
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            # Map sheet names to product categories
            if 'Shower Base' in sheet_name:
                category = 'Shower Base'
            elif 'Shower Door' in sheet_name:
                category = 'Door'
            elif 'Return Panel' in sheet_name:
                category = 'Return Panel'
            elif 'Wall' in sheet_name:
                category = 'Wall'
            elif 'Enclosure' in sheet_name:
                category = 'Enclosure'
            elif 'Shower' in sheet_name and 'Tub' not in sheet_name:
                category = 'Shower'
            elif 'Tub Shower' in sheet_name:
                category = 'Tub Shower'
            elif 'Tub Door' in sheet_name:
                category = 'Tub Door'
            elif 'Bathtub' in sheet_name:
                category = 'Bathtub'
            else:
                category = sheet_name
                
            data[category] = df
            logger.info(f"Loaded {sheet_name} with {len(df)} rows as category {category}")
        
        return data
    
    except Exception as e:
        logger.error(f"Error in load_excel_files: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def import_products(data):
    """Import products from Excel data to database"""
    try:
        # Clear existing data
        with app.app_context():
            db.session.query(Compatibility).delete()
            db.session.query(Product).delete()
            db.session.commit()
            logger.info("Cleared existing database records")
        
        # Process each dataset
        product_count = 0
        
        # First, process all products
        for category, df in data.items():
            
            # Ensure we have a SKU column (various possible names)
            sku_column = None
            for col in df.columns:
                if col.upper() == 'SKU' or col.lower() == 'sku' or col == 'Unique ID':
                    sku_column = col
                    break
            
            if sku_column is None:
                logger.warning(f"No SKU column found in {category} data, skipping")
                continue
                
            # Insert products
            for _, row in df.iterrows():
                sku = str(row.get(sku_column, '')).strip()
                if not sku or pd.isna(sku):
                    continue
                
                # Extract other common product attributes
                product_data = {}
                for col in df.columns:
                    value = row.get(col)
                    # Skip NaN values and convert to appropriate types
                    if not pd.isna(value):
                        product_data[col] = str(value) if not isinstance(value, (int, float)) else value
                
                # Create a product record
                try:
                    # Check if certain columns exist in the dataframe
                    brand = row.get('Brand', None) if 'Brand' in df.columns else None
                    family = row.get('Family', None) if 'Family' in df.columns else None
                    series = row.get('Series', None) if 'Series' in df.columns else None
                    nominal = row.get('Nominal Dimensions', None) if 'Nominal Dimensions' in df.columns else None
                    install = row.get('Installation', None) if 'Installation' in df.columns else None
                    max_door_width = row.get('Max Door Width', None) if 'Max Door Width' in df.columns else None
                    width = row.get('Width', None) if 'Width' in df.columns else None
                    length = row.get('Length', None) if 'Length' in df.columns else None
                    height = row.get('Max Door Height', None) if 'Max Door Height' in df.columns else None
                    
                    # Convert to proper types
                    brand = str(brand) if brand and not pd.isna(brand) else None
                    family = str(family) if family and not pd.isna(family) else None
                    series = str(series) if series and not pd.isna(series) else None
                    nominal = str(nominal) if nominal and not pd.isna(nominal) else None
                    install = str(install) if install and not pd.isna(install) else None
                    
                    # Convert numeric values
                    try:
                        max_door_width = int(max_door_width) if max_door_width and not pd.isna(max_door_width) else None
                    except:
                        max_door_width = None
                        
                    try:
                        width = int(width) if width and not pd.isna(width) else None
                    except:
                        width = None
                        
                    try:
                        length = int(length) if length and not pd.isna(length) else None
                    except:
                        length = None
                        
                    try:
                        height = int(height) if height and not pd.isna(height) else None
                    except:
                        height = None
                    
                    # Get product name from the column
                    product_name = row.get('Product Name', None) if 'Product Name' in df.columns else None
                    if not product_name or pd.isna(product_name):
                        # Generate a product name if one doesn't exist in the Excel
                        if brand and family:
                            product_name = f"{brand} {family} {category}"
                        else:
                            product_name = f"{category} {sku}"
                    else:
                        product_name = str(product_name)
                
                    # Create product object
                    with app.app_context():
                        product = Product(
                            sku=sku,
                            category=category,
                            brand=brand,
                            family=family,
                            series=series,
                            nominal_dimensions=nominal,
                            installation=install,
                            max_door_width=max_door_width,
                            width=width,
                            length=length,
                            height=height,
                            product_data=json.dumps(product_data),
                            product_name=product_name
                        )
                        db.session.add(product)
                        db.session.commit()
                    product_count += 1
                    
                    if product_count % 100 == 0:
                        logger.info(f"Imported {product_count} products so far")
                    
                except Exception as e:
                    logger.error(f"Error inserting product {sku}: {str(e)}")
                    continue
        
        logger.info(f"Imported {product_count} products successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error in import_products: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def series_compatible(base_series, compare_series):
    """Check if two series are compatible"""
    # If either series is not available, consider them compatible
    if not base_series or not compare_series:
        return True
    
    # Exact match
    if base_series.lower() == compare_series.lower():
        return True
    
    # Compatibility matrix of series that work together
    compatible_series = {
        'OBC': ['OBC', 'DW'],
        'DW': ['OBC', 'DW'],
    }
    
    # Check if they're in the compatibility matrix
    base_key = base_series.upper()
    compare_key = compare_series.upper()
    
    if base_key in compatible_series and compare_key in compatible_series[base_key]:
        return True
    
    return False

def brand_family_match_doors(base_brand, base_family, door_brand, door_family):
    """Check if brands and families match for doors compatibility"""
    # If any brand or family is missing, consider it a match
    if not base_brand or not door_brand or not base_family or not door_family:
        return True
    
    # Normalize to uppercase for comparison
    base_brand = base_brand.upper()
    door_brand = door_brand.upper()
    base_family = base_family.upper()
    door_family = door_family.upper()
    
    # Special compatibility for certain brand combinations
    special_compatibility = {
        'MAAX': ['MAAX', 'KINKEAD'],
        'KINKEAD': ['MAAX', 'KINKEAD'],
    }
    
    # Brand match checks
    if base_brand in special_compatibility and door_brand in special_compatibility[base_brand]:
        return True
    
    # If brands don't match in special compatibility, require exact match
    if base_brand != door_brand:
        return False
    
    # Family match checks (these families are compatible across brands)
    compatible_families = {
        'MANHATTAN': ['MANHATTAN'],
        'KLEARA': ['KLEARA'],
        'REVEAL': ['REVEAL'],
        'ESSENCE': ['ESSENCE'],
        'PIVOLOK': ['PIVOLOK'],
        'HALO': ['HALO'],
    }
    
    # Check if the families are in compatible family groups
    if base_family in compatible_families and door_family in compatible_families[base_family]:
        return True
    
    # Family must match if not in compatible families list
    return base_family == door_family

def brand_family_match_walls(base_brand, base_family, wall_brand, wall_family):
    """Check if brands and families match for walls compatibility"""
    # If any brand or family is missing, consider it a match
    if not base_brand or not wall_brand or not base_family or not wall_family:
        return True
    
    # Normalize to uppercase for comparison
    base_brand = base_brand.upper()
    wall_brand = wall_brand.upper()
    base_family = base_family.upper()
    wall_family = wall_family.upper()
    
    # Special compatibility for certain brand combinations
    special_compatibility = {
        'MAAX': ['MAAX', 'AKER', 'AMERICAN STANDARD'],
        'AKER': ['MAAX', 'AKER', 'AMERICAN STANDARD'],
        'AMERICAN STANDARD': ['MAAX', 'AKER', 'AMERICAN STANDARD'],
    }
    
    # Brand match checks
    if base_brand in special_compatibility and wall_brand in special_compatibility[base_brand]:
        return True
    
    # If brands don't match in special compatibility, require exact match
    if base_brand != wall_brand:
        return False
    
    # These families are compatible with any family in the same brand
    universal_families = ['UTILE', 'MODULR']
    if wall_family in universal_families:
        return True
    
    # Family match checks (these families are compatible across brands)
    compatible_families = {
        'MANHATTAN': ['MANHATTAN', 'MODULR', 'UTILE'],
        'KLEARA': ['KLEARA', 'MODULR', 'UTILE'],
        'REVEAL': ['REVEAL', 'MODULR', 'UTILE'],
    }
    
    # Check if the families are in compatible family groups
    if base_family in compatible_families and wall_family in compatible_families[base_family]:
        return True
    
    # Family must match if not in compatible families list
    return base_family == wall_family

def compute_compatibilities():
    """Compute compatibilities between products"""
    try:
        compatibility_count = 0
        
        with app.app_context():
            # Get all shower bases
            bases = db.session.query(Product).filter(Product.category == 'Shower Base').all()
            
            if not bases:
                logger.warning("No shower bases found to process")
                return False
                
            # Get other product categories
            doors = db.session.query(Product).filter(Product.category == 'Door').all()
            walls = db.session.query(Product).filter(Product.category == 'Wall').all()
            
            # Process each base
            for base in bases:
                # Get base properties
                base_data = json.loads(base.product_data) if base.product_data else {}
                
                # Process doors
                for door in doors:
                    door_data = json.loads(door.product_data) if door.product_data else {}
                    
                    # Check door compatibility
                    try:
                        # Get door properties
                        door_type = str(door_data.get("Type", "")).lower() if door_data.get("Type") else ""
                        door_min_width = door_data.get("Minimum Width")
                        door_max_width = door_data.get("Maximum Width")
                        door_has_return = door_data.get("Has Return Panel") == "Yes"
                        
                        # Normalize values
                        if door_min_width and isinstance(door_min_width, str):
                            try:
                                door_min_width = float(door_min_width)
                            except:
                                door_min_width = None
                                
                        if door_max_width and isinstance(door_max_width, str):
                            try:
                                door_max_width = float(door_max_width)
                            except:
                                door_max_width = None
                        
                        # Match doors for alcove installations
                        if (
                            "shower" in door_type and
                            "alcove" in (base.installation or "").lower() and
                            base.max_door_width and door_min_width and door_max_width and
                            door_min_width <= base.max_door_width <= door_max_width and
                            series_compatible(base.series, door.series) and
                            brand_family_match_doors(base.brand, base.family, door.brand, door.family)
                        ):
                            # Create compatibility record
                            compat = Compatibility(
                                source_sku=base.sku,
                                target_sku=door.sku,
                                target_category='Doors',
                                requires_return_panel=None
                            )
                            db.session.add(compat)
                            compatibility_count += 1
                            
                            if compatibility_count % 100 == 0:
                                db.session.commit()
                                logger.info(f"Created {compatibility_count} compatibility relationships")
                                
                    except Exception as e:
                        logger.error(f"Error processing door compatibility for {base.sku} and {door.sku}: {str(e)}")
                
                # Process walls
                for wall in walls:
                    wall_data = json.loads(wall.product_data) if wall.product_data else {}
                    
                    # Check wall compatibility
                    try:
                        # Get wall properties
                        wall_type = str(wall_data.get("Type", "")).lower() if wall_data.get("Type") else ""
                        wall_cut = wall_data.get("Cut to Size") == "Yes"
                        
                        # Calculate dimensions for comparison
                        base_nominal = base.nominal_dimensions
                        wall_nominal = wall.nominal_dimensions
                        
                        # Match walls that are compatible with the base
                        if (
                            "alcove" in wall_type and
                            "alcove" in (base.installation or "").lower() and
                            series_compatible(base.series, wall.series) and
                            brand_family_match_walls(base.brand, base.family, wall.brand, wall.family) and
                            (
                                (base_nominal == wall_nominal) or
                                (wall_cut and base.length and wall.length and base.width and wall.width and
                                 base.length <= wall.length and base.width <= wall.width)
                            )
                        ):
                            # Create compatibility record
                            compat = Compatibility(
                                source_sku=base.sku,
                                target_sku=wall.sku,
                                target_category='Walls',
                                requires_return_panel=None
                            )
                            db.session.add(compat)
                            compatibility_count += 1
                            
                            if compatibility_count % 100 == 0:
                                db.session.commit()
                                logger.info(f"Created {compatibility_count} compatibility relationships")
                    
                    except Exception as e:
                        logger.error(f"Error processing wall compatibility for {base.sku} and {wall.sku}: {str(e)}")
            
            # Final commit
            db.session.commit()
            logger.info(f"Created {compatibility_count} compatibility relationships successfully")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in compute_compatibilities: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main import and process function"""
    logger.info("Starting data import and compatibility processing")
    
    # Load data from Excel files
    data = load_excel_files()
    if not data:
        logger.error("Failed to load Excel data")
        return False
    
    # Import products
    logger.info("Importing products to database")
    if not import_products(data):
        logger.error("Failed to import products")
        return False
    
    # Compute compatibilities
    logger.info("Computing compatibility relationships")
    if not compute_compatibilities():
        logger.error("Failed to compute compatibilities")
        return False
    
    logger.info("Data import and compatibility processing completed successfully")
    return True

if __name__ == "__main__":
    main()