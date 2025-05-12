"""
Compatibility Excel Importer

This script imports product and compatibility data directly from an Excel file
where all relationships are pre-defined.

Format for the Excel file:
1. 'Products' sheet with columns: SKU, Category, Brand, Family, Series, Nominal_Dimensions, Product_Name
2. 'Compatibilities' sheet with columns: Source_SKU, Target_SKU, Target_Category, Requires_Return_Panel
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
logger = logging.getLogger('compatibility_excel_importer')

def load_excel_file(file_path):
    """Load products and compatibilities from the Excel file"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        logger.info(f"Loading compatibility data from: {file_path}")
        
        # Load product data
        products_df = pd.read_excel(file_path, sheet_name='Products')
        logger.info(f"Loaded {len(products_df)} products")
        
        # Load compatibility data
        compat_df = pd.read_excel(file_path, sheet_name='Compatibilities')
        logger.info(f"Loaded {len(compat_df)} compatibility relationships")
        
        return {
            'products': products_df,
            'compatibilities': compat_df
        }
    
    except Exception as e:
        logger.error(f"Error loading Excel file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def import_data(data):
    """Import products and compatibilities into database"""
    try:
        # Clear existing data
        with app.app_context():
            logger.info("Clearing existing database records")
            db.session.query(Compatibility).delete()
            db.session.query(Product).delete()
            db.session.commit()
            
            # Import products
            products_df = data['products']
            product_count = 0
            
            for _, row in products_df.iterrows():
                sku = str(row.get('SKU', '')).strip()
                if not sku:
                    continue
                
                # Extract product attributes
                category = row.get('Category')
                brand = row.get('Brand')
                family = row.get('Family')
                series = row.get('Series')
                nominal_dimensions = row.get('Nominal_Dimensions')
                product_name = row.get('Product_Name')
                
                # Additional attributes if available
                product_data = {}
                for col in products_df.columns:
                    value = row.get(col)
                    if not pd.isna(value):
                        product_data[col] = str(value) if not isinstance(value, (int, float)) else value
                
                # Create product record
                product = Product(
                    sku=sku,
                    category=category,
                    brand=brand,
                    family=family,
                    series=series,
                    nominal_dimensions=nominal_dimensions,
                    product_name=product_name,
                    product_data=json.dumps(product_data)
                )
                
                # Add numeric dimensions if available
                if 'Width' in products_df.columns:
                    product.width = row.get('Width') if not pd.isna(row.get('Width')) else None
                
                if 'Length' in products_df.columns:
                    product.length = row.get('Length') if not pd.isna(row.get('Length')) else None
                
                if 'Height' in products_df.columns:
                    product.height = row.get('Height') if not pd.isna(row.get('Height')) else None
                
                if 'Max_Door_Width' in products_df.columns:
                    product.max_door_width = row.get('Max_Door_Width') if not pd.isna(row.get('Max_Door_Width')) else None
                
                if 'Installation' in products_df.columns:
                    product.installation = row.get('Installation') if not pd.isna(row.get('Installation')) else None
                
                db.session.add(product)
                product_count += 1
                
                if product_count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Imported {product_count} products so far")
            
            db.session.commit()
            logger.info(f"Imported {product_count} products into database")
            
            # Import compatibilities
            compat_df = data['compatibilities']
            compat_count = 0
            
            for _, row in compat_df.iterrows():
                source_sku = str(row.get('Source_SKU', '')).strip()
                target_sku = str(row.get('Target_SKU', '')).strip()
                target_category = row.get('Target_Category')
                requires_return_panel = row.get('Requires_Return_Panel') if not pd.isna(row.get('Requires_Return_Panel')) else None
                
                if not source_sku or not target_sku or not target_category:
                    continue
                
                compat = Compatibility(
                    source_sku=source_sku,
                    target_sku=target_sku,
                    target_category=target_category,
                    requires_return_panel=requires_return_panel
                )
                
                db.session.add(compat)
                compat_count += 1
                
                if compat_count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Imported {compat_count} compatibility relationships so far")
            
            db.session.commit()
            logger.info(f"Imported {compat_count} compatibility relationships into database")
            
            return True
    
    except Exception as e:
        logger.error(f"Error importing data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_sample_compatibility_excel():
    """Create a sample compatibility Excel file with our existing data"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'data', 'Compatibility_Data.xlsx')
        
        with app.app_context():
            # Get all products
            products = db.session.query(Product).all()
            
            # Extract product data
            products_data = []
            for product in products:
                # Extract product data
                product_data = {
                    'SKU': product.sku,
                    'Category': product.category,
                    'Brand': product.brand,
                    'Family': product.family,
                    'Series': product.series,
                    'Nominal_Dimensions': product.nominal_dimensions,
                    'Product_Name': product.product_name,
                    'Width': product.width,
                    'Length': product.length,
                    'Height': product.height,
                    'Max_Door_Width': product.max_door_width,
                    'Installation': product.installation
                }
                products_data.append(product_data)
            
            # Create DataFrame
            products_df = pd.DataFrame(products_data)
            
            # Get all compatibilities
            compatibilities = db.session.query(Compatibility).all()
            
            # Extract compatibility data
            compatibilities_data = []
            for compat in compatibilities:
                compat_data = {
                    'Source_SKU': compat.source_sku,
                    'Target_SKU': compat.target_sku,
                    'Target_Category': compat.target_category,
                    'Requires_Return_Panel': compat.requires_return_panel
                }
                compatibilities_data.append(compat_data)
            
            # Create DataFrame
            compatibilities_df = pd.DataFrame(compatibilities_data)
            
            # Create Excel writer
            with pd.ExcelWriter(file_path) as writer:
                products_df.to_excel(writer, sheet_name='Products', index=False)
                compatibilities_df.to_excel(writer, sheet_name='Compatibilities', index=False)
                
            logger.info(f"Created sample compatibility Excel file: {file_path}")
            return file_path
    
    except Exception as e:
        logger.error(f"Error creating sample compatibility Excel file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """Main function"""
    logger.info("Starting compatibility Excel import")
    
    # Check if the compatibility file exists
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'Compatibility_Data.xlsx')
    
    if not os.path.exists(file_path):
        logger.info("Compatibility file does not exist. Creating a sample file.")
        file_path = create_sample_compatibility_excel()
        
        if not file_path:
            logger.error("Failed to create sample compatibility file")
            return False
        
        logger.info(f"Created sample compatibility file: {file_path}")
        logger.info("Please update this file with all the compatibility data and run this script again.")
        return True
    
    # Load data from Excel file
    data = load_excel_file(file_path)
    if not data:
        logger.error("Failed to load data from Excel file")
        return False
    
    # Import data into database
    if not import_data(data):
        logger.error("Failed to import data into database")
        return False
    
    logger.info("Compatibility data imported successfully")
    return True

if __name__ == "__main__":
    main()