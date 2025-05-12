"""
Load real data from the Excel files in the data directory.
"""
import os
import sys
import pandas as pd
import json
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
logger = logging.getLogger('data_loader')

def main():
    # Database connection
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        logger.error("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Load the Excel file
    excel_path = os.path.join('data', 'Product Data.xlsx')
    if not os.path.exists(excel_path):
        logger.error(f"Error: Excel file not found at {excel_path}")
        sys.exit(1)
        
    logger.info(f"Loading product data from {excel_path}")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    try:
        # Load Excel file
        excel_file = pd.ExcelFile(excel_path)
        
        # Check what sheets are available
        sheet_names = excel_file.sheet_names
        logger.info(f"Excel file contains sheets: {sheet_names}")
        
        # First, clear all existing data
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE products CASCADE"))
            conn.execute(text("TRUNCATE TABLE compatibilities"))
            conn.commit()
            logger.info("Cleared existing product and compatibility data")
        
        # Process each sheet and load product data
        sheets_to_process = [
            ("Shower Bases", "Shower Base"),
            ("Shower Doors", "Door"),
            ("Return Panels", "Return Panel"),
            ("Walls", "Wall"),
            ("Enclosures", "Enclosure")
        ]
        
        product_count = 0
        
        for sheet_name, category in sheets_to_process:
            if sheet_name in sheet_names:
                logger.info(f"Processing sheet: {sheet_name}")
                try:
                    # Read sheet
                    df = excel_file.parse(sheet_name)
                    
                    # Check required columns
                    required_columns = ['Unique ID', 'Brand', 'Family', 'Series']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        logger.warning(f"Sheet {sheet_name} is missing required columns: {missing_columns}")
                        continue
                        
                    # Process each row
                    for _, row in df.iterrows():
                        sku = row.get('Unique ID')
                        if pd.isna(sku) or not sku:
                            continue
                            
                        # Extract common fields
                        brand = row.get('Brand')
                        family = row.get('Family')
                        series = row.get('Series')
                        nominal_dimensions = row.get('Nominal Dimensions')
                        
                        # Extract size dimensions based on category
                        width = None
                        length = None
                        height = None
                        max_door_width = None
                        installation = None
                        
                        if category == "Shower Base":
                            width = row.get('Width')
                            length = row.get('Length')
                            max_door_width = row.get('Max Door Width')
                            installation = row.get('Installation')
                        elif category == "Door":
                            width = row.get('Maximum Width')
                            height = row.get('Height')
                        elif category == "Wall":
                            width = row.get('Width')
                            length = row.get('Length')
                            height = row.get('Height')
                        
                        # Save remaining data as JSON
                        row_dict = row.to_dict()
                        # Remove columns we've already processed
                        for col in ['Unique ID', 'Brand', 'Family', 'Series', 
                                   'Nominal Dimensions', 'Width', 'Length', 'Height', 
                                   'Max Door Width', 'Installation']:
                            if col in row_dict:
                                del row_dict[col]
                                
                        # Handle compatibility columns
                        if 'Compatible Doors' in row_dict:
                            doors_value = row_dict['Compatible Doors']
                            del row_dict['Compatible Doors']
                        else:
                            doors_value = None
                            
                        if 'Compatible Walls' in row_dict:
                            walls_value = row_dict['Compatible Walls']
                            del row_dict['Compatible Walls']
                        else:
                            walls_value = None
                        
                        # Convert to JSON string
                        product_data = json.dumps(row_dict)
                        
                        try:
                            # Insert product into database
                            with engine.connect() as conn:
                                conn.execute(text("""
                                    INSERT INTO products 
                                    (sku, category, brand, family, series, nominal_dimensions, 
                                    installation, max_door_width, width, length, height, product_data) 
                                    VALUES (:sku, :category, :brand, :family, :series, :nominal_dimensions, 
                                    :installation, :max_door_width, :width, :length, :height, :product_data)
                                """), {
                                    'sku': sku,
                                    'category': category,
                                    'brand': brand,
                                    'family': family, 
                                    'series': series,
                                    'nominal_dimensions': nominal_dimensions,
                                    'installation': installation,
                                    'max_door_width': max_door_width,
                                    'width': width,
                                    'length': length,
                                    'height': height,
                                    'product_data': product_data
                                })
                                conn.commit()
                                product_count += 1
                                
                                # Process compatibility data if present
                                if category == "Shower Base" and doors_value and not pd.isna(doors_value):
                                    doors = str(doors_value).split('|')
                                    for door in doors:
                                        door = door.strip()
                                        if not door:
                                            continue
                                            
                                        # Handle case where it might have a return panel
                                        return_panel = None
                                        if '|' in door:
                                            door_parts = door.split('|')
                                            door = door_parts[0].strip()
                                            if len(door_parts) > 1:
                                                return_panel = door_parts[1].strip()
                                        
                                        conn.execute(text("""
                                            INSERT INTO compatibilities 
                                            (source_sku, target_sku, target_category, requires_return_panel) 
                                            VALUES (:source, :target, :category, :return_panel)
                                        """), {
                                            'source': sku,
                                            'target': door,
                                            'category': 'Doors',
                                            'return_panel': return_panel
                                        })
                                        conn.commit()
                                
                                if category == "Shower Base" and walls_value and not pd.isna(walls_value):
                                    walls = str(walls_value).split('|')
                                    for wall in walls:
                                        wall = wall.strip()
                                        if not wall:
                                            continue
                                            
                                        conn.execute(text("""
                                            INSERT INTO compatibilities 
                                            (source_sku, target_sku, target_category, requires_return_panel) 
                                            VALUES (:source, :target, :category, :return_panel)
                                        """), {
                                            'source': sku,
                                            'target': wall,
                                            'category': 'Walls',
                                            'return_panel': None
                                        })
                                        conn.commit()
                                
                        except Exception as e:
                            logger.error(f"Error inserting product {sku}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error processing sheet {sheet_name}: {e}")
            else:
                logger.warning(f"Sheet {sheet_name} not found in Excel file")
        
        logger.info(f"Successfully loaded {product_count} products")
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")

if __name__ == "__main__":
    main()