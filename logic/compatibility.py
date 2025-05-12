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
        dict: Dictionary containing DataFrames of product data, with sheet names as keys
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
        
        # Load each Excel file, reading all worksheets
        for file_path in excel_files:
            try:
                # Use pd.ExcelFile to get all sheet names
                excel = pd.ExcelFile(file_path)
                sheet_names = excel.sheet_names
                
                # Load each worksheet into a separate DataFrame
                for sheet_name in sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    # Use the sheet name as the key in the data dictionary
                    data[sheet_name] = df
                    logger.debug(f"Loaded worksheet '{sheet_name}' with {len(df)} rows")
                
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
        # Load all data from worksheets
        data = load_data()
        
        if not data:
            logger.warning("No data available for compatibility search")
            return []
        
        # Find the product in the data
        product_info = None
        product_category = None
        
        for category, df in data.items():
            # Check if 'Unique ID' column exists in the DataFrame (main identifier in the Excel file)
            id_column = None
            for col in df.columns:
                if col == 'Unique ID':
                    id_column = col
                    break
            
            if id_column is None:
                logger.warning(f"No Unique ID column found in {category} data")
                continue
            
            # Try to find the SKU in this category
            # Convert everything to string and uppercase for case-insensitive comparison
            product_row = df[df[id_column].astype(str).str.upper() == sku.upper()]
            
            if not product_row.empty:
                product_info = product_row.iloc[0].to_dict()
                product_category = category
                logger.debug(f"Found product in category: {category}")
                break
        
        if product_info is None:
            logger.warning(f"No product found for SKU: {sku}")
            return []
        
        # This is a placeholder for your actual compatibility logic
        # You will need to paste your existing compatibility scripts here
        # The returned structure should be a list of dictionaries, where each dictionary has:
        # - 'category': The product category
        # - 'skus': A list of compatible SKU strings
        
        # PLACEHOLDER COMPATIBILITY LOGIC - REPLACE WITH YOUR OWN SCRIPTS
        # For demonstration purposes only
        compatible_products = []
        
        # Example: If we found a Shower Base, we might show sample compatible doors and walls
        if product_category == 'Shower Bases':
            # Just a placeholder - your actual logic will determine real compatible products
            compatible_products = [
                {
                    "category": "Shower Doors",
                    "skus": ["Example Door SKU 1", "Example Door SKU 2"] 
                },
                {
                    "category": "Walls",
                    "skus": ["Example Wall SKU 1", "Example Wall SKU 2"]
                }
            ]
        
        logger.debug(f"Found {len(compatible_products)} compatible categories")
        return compatible_products
        
        # ******************************************************************
        # INSERT YOUR COMPATIBILITY MATCHING LOGIC BELOW THIS LINE
        # ******************************************************************
        # The existing data structure:
        # - 'data' is a dictionary where keys are worksheet names and values are pandas DataFrames
        # - 'product_info' contains the product details as a dictionary
        # - 'product_category' is the name of the worksheet where the product was found
        # 
        # Return a list of dictionaries in this format:
        # [
        #    {"category": "Category Name", "skus": ["SKU1", "SKU2", "SKU3"]},
        #    {"category": "Another Category", "skus": ["SKU4", "SKU5"]}
        # ]
        # ******************************************************************
        
    except Exception as e:
        logger.error(f"Error in find_compatible_products: {str(e)}")
        return []

# Note: This placeholder implementation should be replaced with the actual
# compatibility logic from the existing scripts when they are provided.
# The user will need to paste their existing compatibility scripts into this file
# or create additional modules in the logic directory.
