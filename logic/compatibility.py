import os
import pandas as pd
import logging
import glob

# Configure logging
logger = logging.getLogger(__name__)

def load_data():
    """
    Load master data files from the /data/ folder
    
    Returns:
        dict: Dictionary containing DataFrames of product data
    """
    data = {}
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        logger.debug(f"Looking for data files in: {data_path}")
        
        # Find all Excel files in the data directory
        excel_files = glob.glob(os.path.join(data_path, "*.xlsx"))
        logger.debug(f"Found Excel files: {excel_files}")
        
        if not excel_files:
            logger.warning("No Excel files found in the data directory")
            return data
        
        # Load each Excel file into a DataFrame
        for file_path in excel_files:
            file_name = os.path.basename(file_path).replace('.xlsx', '')
            try:
                df = pd.read_excel(file_path)
                data[file_name] = df
                logger.debug(f"Loaded {file_name} with {len(df)} rows")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
        
        return data
    
    except Exception as e:
        logger.error(f"Error in load_data: {str(e)}")
        return {}

def find_compatible_products(sku):
    """
    Find compatible products for a given SKU
    
    Args:
        sku (str): The SKU to search for
    
    Returns:
        list: List of dictionaries containing category and compatible SKUs
    """
    try:
        # Load all data
        data = load_data()
        
        if not data:
            logger.warning("No data available for compatibility search")
            return []
        
        # Find the product in the data
        product_info = None
        product_category = None
        
        for category, df in data.items():
            # Check if 'SKU' column exists in the DataFrame
            sku_column = None
            for col in df.columns:
                if col.upper() == 'SKU' or col.lower() == 'sku':
                    sku_column = col
                    break
            
            if sku_column is None:
                logger.warning(f"No SKU column found in {category} data")
                continue
            
            # Try to find the SKU in this category
            product_row = df[df[sku_column].astype(str).str.upper() == sku.upper()]
            
            if not product_row.empty:
                product_info = product_row.iloc[0].to_dict()
                product_category = category
                logger.debug(f"Found product in category: {category}")
                break
        
        if product_info is None:
            logger.warning(f"No product found for SKU: {sku}")
            return []
        
        # Find compatible products
        compatible_products = []
        
        # This is a placeholder for the actual compatibility logic
        # The real implementation would use the existing compatibility scripts
        # that would be placed in this directory
        
        # Example structure (to be replaced with actual compatibility logic):
        # The structure assumes we have compatibility rules defined somewhere
        for category, df in data.items():
            if category == product_category:
                continue  # Skip the product's own category
                
            compatible_skus = []
            
            # This would be replaced with the actual compatibility checking logic
            # For now, we'll just add a placeholder
            compatible_skus = ["Sample-SKU-1", "Sample-SKU-2"]
            
            if compatible_skus:
                compatible_products.append({
                    "category": category,
                    "skus": compatible_skus
                })
        
        logger.debug(f"Found {len(compatible_products)} compatible categories")
        return compatible_products
    
    except Exception as e:
        logger.error(f"Error in find_compatible_products: {str(e)}")
        return []

# Note: This placeholder implementation should be replaced with the actual
# compatibility logic from the existing scripts when they are provided.
# The user will need to paste their existing compatibility scripts into this file
# or create additional modules in the logic directory.
