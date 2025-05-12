import os
import sys
import json
import logging
import pandas as pd
import time
from datetime import datetime
import traceback
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('data_updater')

# Get the database connection string from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

# Global tracking variables
last_run_time = None
process_status = "Idle"

def load_excel_files():
    """Load all Excel files from the data directory"""
    data = {}
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data')
        logger.info(f"Loading Excel files from: {data_path}")
        
        # Find all Excel files in the data directory
        excel_files = []
        for file in os.listdir(data_path):
            if file.endswith('.xlsx'):
                excel_files.append(os.path.join(data_path, file))
        
        if not excel_files:
            logger.warning("No Excel files found in the data directory")
            return data
        
        # Load each Excel file into a DataFrame
        for file_path in excel_files:
            file_name = os.path.basename(file_path).replace('.xlsx', '')
            try:
                # Get list of sheet names
                excel_file = pd.ExcelFile(file_path)
                
                # Load each sheet
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    # Create a unique key combining file and sheet name
                    key = f"{file_name}_{sheet_name}"
                    data[key] = df
                    logger.info(f"Loaded {key} with {len(df)} rows")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
        
        return data
    
    except Exception as e:
        logger.error(f"Error in load_excel_files: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def update_database(data):
    """Update the database with product and compatibility data"""
    global process_status
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    process_status = "Updating database"
    
    try:
        # Create database engine
        engine = create_engine(DATABASE_URL)
        
        # Clear existing data
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE compatibilities CASCADE"))
            conn.execute(text("TRUNCATE TABLE products CASCADE"))
            conn.commit()
            logger.info("Cleared existing database records")
        
        # Process each dataset
        product_count = 0
        compatibility_count = 0
        
        # First, process all products
        for key, df in data.items():
            category = key.split('_')[1] if '_' in key else key
            
            # Ensure we have a SKU column (various possible names)
            sku_column = None
            for col in df.columns:
                if col.upper() == 'SKU' or col.lower() == 'sku' or 'unique id' in col.lower():
                    sku_column = col
                    break
            
            if sku_column is None:
                logger.warning(f"No SKU column found in {key} data, skipping")
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
                    # Insert into products table
                    with engine.connect() as conn:
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
                        
                        # Prepare query
                        insert_query = text("""
                            INSERT INTO products 
                            (sku, category, brand, family, series, nominal_dimensions, installation, 
                            max_door_width, width, length, height, product_data) 
                            VALUES (:sku, :category, :brand, :family, :series, :nominal, :install,
                            :max_door_width, :width, :length, :height, :product_data)
                            ON CONFLICT (sku) DO UPDATE SET
                            category = :category,
                            brand = :brand,
                            family = :family,
                            series = :series,
                            nominal_dimensions = :nominal,
                            installation = :install,
                            max_door_width = :max_door_width,
                            width = :width,
                            length = :length,
                            height = :height,
                            product_data = :product_data
                        """)
                        
                        conn.execute(insert_query, {
                            'sku': sku,
                            'category': category,
                            'brand': brand,
                            'family': family,
                            'series': series,
                            'nominal': nominal,
                            'install': install,
                            'max_door_width': max_door_width,
                            'width': width,
                            'length': length,
                            'height': height,
                            'product_data': json.dumps(product_data)
                        })
                        conn.commit()
                    product_count += 1
                except Exception as e:
                    logger.error(f"Error inserting product {sku}: {str(e)}")
                    continue
        
        logger.info(f"Inserted {product_count} products")
        
        # Now process compatibility relationships
        for key, df in data.items():
            category = key.split('_')[1] if '_' in key else key
            
            # Ensure we have a SKU column and compatibility columns
            sku_column = None
            for col in df.columns:
                if col.upper() == 'SKU' or col.lower() == 'sku' or 'unique id' in col.lower():
                    sku_column = col
                    break
            
            if sku_column is None:
                logger.warning(f"No SKU column found in {key} data, skipping compatibility check")
                continue
            
            # Look for compatibility columns
            compatibility_columns = []
            for col in df.columns:
                if 'compatible' in col.lower():
                    compatibility_columns.append(col)
            
            if not compatibility_columns:
                logger.warning(f"No compatibility columns found in {key} data")
                continue
            
            # Process compatibility data
            for _, row in df.iterrows():
                source_sku = str(row.get(sku_column, '')).strip()
                if not source_sku or pd.isna(source_sku):
                    continue
                
                # Process each compatibility column
                for compat_col in compatibility_columns:
                    compat_value = row.get(compat_col, '')
                    if pd.isna(compat_value) or not compat_value:
                        continue
                    
                    # Determine target category from column name
                    # e.g., "Compatible Doors" -> "Doors"
                    target_category = compat_col.replace('Compatible ', '').strip()
                    
                    # Split by delimiter |
                    if isinstance(compat_value, str):
                        skus = compat_value.split('|')
                        for sku_entry in skus:
                            sku_entry = sku_entry.strip()
                            if not sku_entry:
                                continue
                            
                            # Handle special case: SKU with return panel
                            requires_return_panel = None
                            target_sku = sku_entry
                            
                            # Check if this is a compound entry with return panel
                            if '(' in sku_entry and ')' in sku_entry:
                                parts = sku_entry.split('(')
                                target_sku = parts[0].strip()
                                requires_info = parts[1].strip()
                                if 'return panel' in requires_info.lower():
                                    # Extract the return panel SKU
                                    panel_info = requires_info.replace(')', '').strip()
                                    panel_parts = panel_info.split(':')
                                    if len(panel_parts) > 1:
                                        requires_return_panel = panel_parts[1].strip()
                            
                            # Insert into compatibilities table
                            try:
                                with engine.connect() as conn:
                                    insert_query = text("""
                                        INSERT INTO compatibilities 
                                        (source_sku, target_sku, target_category, requires_return_panel) 
                                        VALUES (:source_sku, :target_sku, :target_category, :requires_return_panel)
                                        ON CONFLICT (id) DO NOTHING
                                    """)
                                    
                                    conn.execute(insert_query, {
                                        'source_sku': source_sku,
                                        'target_sku': target_sku,
                                        'target_category': target_category,
                                        'requires_return_panel': requires_return_panel
                                    })
                                    conn.commit()
                                compatibility_count += 1
                            except Exception as e:
                                logger.error(f"Error inserting compatibility {source_sku} -> {target_sku}: {str(e)}")
                                continue
        
        logger.info(f"Inserted {compatibility_count} compatibility relationships")
        process_status = "Complete"
        return True
    
    except Exception as e:
        logger.error(f"Error in update_database: {str(e)}")
        logger.error(traceback.format_exc())
        process_status = "Error"
        return False

def run_update_process():
    """Run the complete update process"""
    global last_run_time, process_status
    
    process_status = "Loading data"
    logger.info("Starting data update process")
    
    # Load Excel data
    data = load_excel_files()
    if not data:
        logger.error("No data loaded, update process aborted")
        process_status = "Failed - No data"
        return
    
    # Update database
    success = update_database(data)
    
    if success:
        logger.info("Data update process completed successfully")
        last_run_time = datetime.now()
    else:
        logger.error("Data update process failed")
        process_status = "Failed"

def get_status():
    """Get the current status of the updater"""
    return {
        'last_run': last_run_time.strftime('%Y-%m-%d %H:%M:%S') if last_run_time else None,
        'status': process_status
    }

if __name__ == "__main__":
    # Run once immediately
    run_update_process()
    
    # Then run every hour
    while True:
        # Sleep for one hour
        time.sleep(3600)
        run_update_process()