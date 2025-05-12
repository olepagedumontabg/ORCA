import os
import pandas as pd
import logging
import glob
from logic import base_compatibility
from logic import image_handler

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
        dict: Dictionary containing source product info and compatible products
    """
    try:
        # Load all data from worksheets
        data = load_data()
        
        if not data:
            logger.warning("No data available for compatibility search")
            return {"product": None, "compatibles": []}
        
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
            return {"product": None, "compatibles": []}
        
        # Set up the empty results list
        compatible_products = []
        
        # Call the appropriate compatibility logic based on product category
        if product_category == 'Shower Bases':
            # Use the dedicated shower base compatibility logic
            compatible_categories = base_compatibility.find_base_compatibilities(data, product_info)
            
            # Enhance the results with additional product details
            for category_info in compatible_categories:
                category = category_info["category"]
                enhanced_skus = []
                
                for sku_item in category_info["skus"]:
                    # Check if this is a combined SKU (door + return panel)
                    if "|" in sku_item:
                        door_sku, panel_sku = sku_item.split("|")
                        door_info = get_product_details(data, door_sku)
                        panel_info = get_product_details(data, panel_sku)
                        
                        if door_info and panel_info:
                            enhanced_skus.append({
                                "sku": sku_item,
                                "is_combo": True,
                                "main_product": {
                                    "sku": door_sku,
                                    "name": door_info.get("Product Name", ""),
                                    "image_url": image_handler.generate_image_url(door_info),
                                    "nominal_dimensions": door_info.get("Nominal Dimensions", "")
                                },
                                "secondary_product": {
                                    "sku": panel_sku,
                                    "name": panel_info.get("Product Name", ""),
                                    "image_url": image_handler.generate_image_url(panel_info),
                                    "nominal_dimensions": panel_info.get("Nominal Dimensions", "")
                                }
                            })
                    else:
                        product_info = get_product_details(data, sku_item)
                        if product_info:
                            enhanced_skus.append({
                                "sku": sku_item,
                                "is_combo": False,
                                "name": product_info.get("Product Name", ""),
                                "image_url": image_handler.generate_image_url(product_info),
                                "nominal_dimensions": product_info.get("Nominal Dimensions", ""),
                                "brand": product_info.get("Brand", ""),
                                "series": product_info.get("Series", "")
                            })
                
                compatible_products.append({
                    "category": category,
                    "products": enhanced_skus
                })
        
        # Additional categories can be added here with their own dedicated modules
        # elif product_category == 'Shower Doors':
        #     compatible_products = door_compatibility.find_door_compatibilities(data, product_info)
        # etc.
        
        # If no specific compatibility logic matched or no compatible products found,
        # check if there are explicit compatibility columns in the product info
        if not compatible_products and product_info is not None:
            # Check for explicitly listed compatible doors
            if 'Compatible Doors' in product_info and product_info.get('Compatible Doors') and pd.notna(product_info['Compatible Doors']):
                doors_value = str(product_info['Compatible Doors'])
                if '|' in doors_value:
                    # Pipe-delimited values
                    compatible_doors = doors_value.split('|')
                else:
                    # Comma-delimited values
                    compatible_doors = doors_value.split(',')
                
                enhanced_skus = []
                for door_sku in [door.strip() for door in compatible_doors if door.strip()]:
                    door_info = get_product_details(data, door_sku)
                    if door_info:
                        enhanced_skus.append({
                            "sku": door_sku,
                            "is_combo": False,
                            "name": door_info.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(door_info),
                            "nominal_dimensions": door_info.get("Nominal Dimensions", ""),
                            "brand": door_info.get("Brand", ""),
                            "series": door_info.get("Series", "")
                        })
                
                if enhanced_skus:
                    compatible_products.append({
                        "category": "Doors",
                        "products": enhanced_skus
                    })
                
            # Check for explicitly listed compatible walls
            if 'Compatible Walls' in product_info and product_info.get('Compatible Walls') and pd.notna(product_info['Compatible Walls']):
                walls_value = str(product_info['Compatible Walls'])
                if '|' in walls_value:
                    # Pipe-delimited values
                    compatible_walls = walls_value.split('|')
                else:
                    # Comma-delimited values
                    compatible_walls = walls_value.split(',')
                
                enhanced_skus = []
                for wall_sku in [wall.strip() for wall in compatible_walls if wall.strip()]:
                    wall_info = get_product_details(data, wall_sku)
                    if wall_info:
                        enhanced_skus.append({
                            "sku": wall_sku,
                            "is_combo": False,
                            "name": wall_info.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(wall_info),
                            "nominal_dimensions": wall_info.get("Nominal Dimensions", ""),
                            "brand": wall_info.get("Brand", ""),
                            "series": wall_info.get("Series", "")
                        })
                
                if enhanced_skus:
                    compatible_products.append({
                        "category": "Walls", 
                        "products": enhanced_skus
                    })
        
        # Extract important details about the source product directly from product_info
        # This ensures we're using the info of the source product, not a compatible one
        source_product = {
            "sku": sku,
            "category": product_category
        }
        
        # Add additional details if product_info exists
        if product_info is not None:
            # Make sure we're using the correct product information from the base product
            source_product.update({
                "name": product_info.get("Product Name", ""),
                "image_url": image_handler.generate_image_url(product_info),
                "nominal_dimensions": product_info.get("Nominal Dimensions", ""),
                "installation": product_info.get("Installation", ""),
                "brand": product_info.get("Brand", ""),
                "series": product_info.get("Series", ""),
                "family": product_info.get("Family", "")
            })
        
        logger.debug(f"Found {len(compatible_products)} compatible categories")
        return {
            "product": source_product,
            "compatibles": compatible_products
        }
    
    except Exception as e:
        logger.error(f"Error in find_compatible_products: {str(e)}")
        return {"product": None, "compatibles": []}

def get_product_details(data, sku):
    """
    Get product details by SKU from any worksheet
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        sku (str): The SKU to search for
        
    Returns:
        dict: Product details or None if not found
    """
    try:
        for category, df in data.items():
            # Skip any dataframes without a Unique ID column
            if 'Unique ID' not in df.columns:
                continue
                
            # Find the product in this category
            product_row = df[df['Unique ID'].astype(str).str.upper() == sku.upper()]
            
            if not product_row.empty:
                return product_row.iloc[0].to_dict()
                
        return None
    except Exception as e:
        logger.error(f"Error in get_product_details: {str(e)}")
        return None

# Note: This placeholder implementation should be replaced with the actual
# compatibility logic from the existing scripts when they are provided.
# The user will need to paste their existing compatibility scripts into this file
# or create additional modules in the logic directory.
