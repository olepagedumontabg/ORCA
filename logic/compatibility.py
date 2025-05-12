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
        
        # Find compatible products based on the product's category
        compatible_products = []
        
        # Different compatibility logic based on the product category
        if product_category == 'Shower Bases':
            # Shower Base compatibility
            # Compatible with doors, walls, and enclosures
            shower_base_width = product_info.get('Width')
            shower_base_length = product_info.get('Length')
            installation_type = product_info.get('Installation')
            max_door_width = product_info.get('Max Door Width')
            fits_return_panel = product_info.get('Fits Return Panel Size')
            
            # Find compatible doors
            if 'Shower Doors' in data and max_door_width is not None:
                doors_df = data['Shower Doors']
                compatible_doors = doors_df[doors_df['Door Width'] <= max_door_width]
                door_skus = compatible_doors['Unique ID'].astype(str).tolist()
                
                if door_skus:
                    compatible_products.append({
                        "category": "Shower Doors",
                        "skus": door_skus
                    })
            
            # Find compatible walls
            if 'Walls' in data and shower_base_length is not None and shower_base_width is not None:
                walls_df = data['Walls']
                # Find walls that match the base dimensions
                compatible_walls = walls_df[
                    (walls_df['Base Length'] == shower_base_length) & 
                    (walls_df['Base Width'] == shower_base_width)
                ]
                wall_skus = compatible_walls['Unique ID'].astype(str).tolist()
                
                if wall_skus:
                    compatible_products.append({
                        "category": "Walls",
                        "skus": wall_skus
                    })
            
            # Find compatible return panels if it's a corner installation
            if 'Return Panels' in data and fits_return_panel is not None and installation_type == 'Corner':
                panels_df = data['Return Panels']
                compatible_panels = panels_df[panels_df['Return Panel Size'] == fits_return_panel]
                panel_skus = compatible_panels['Unique ID'].astype(str).tolist()
                
                if panel_skus:
                    compatible_products.append({
                        "category": "Return Panels",
                        "skus": panel_skus
                    })
                    
        elif product_category == 'Showers':
            # Showers compatibility
            # They might be compatible with doors
            shower_width = product_info.get('Width')
            
            if 'Shower Doors' in data and shower_width is not None:
                doors_df = data['Shower Doors']
                # Find doors that fit this shower width
                compatible_doors = doors_df[doors_df['Door Width'] <= shower_width]
                door_skus = compatible_doors['Unique ID'].astype(str).tolist()
                
                if door_skus:
                    compatible_products.append({
                        "category": "Shower Doors",
                        "skus": door_skus
                    })
                    
        elif product_category == 'Shower Doors':
            # Shower doors compatibility
            # They might fit certain bases and showers
            door_width = product_info.get('Door Width')
            
            if 'Shower Bases' in data and door_width is not None:
                bases_df = data['Shower Bases']
                # Find bases that can fit this door
                compatible_bases = bases_df[bases_df['Max Door Width'] >= door_width]
                base_skus = compatible_bases['Unique ID'].astype(str).tolist()
                
                if base_skus:
                    compatible_products.append({
                        "category": "Shower Bases",
                        "skus": base_skus
                    })
            
            if 'Showers' in data and door_width is not None:
                showers_df = data['Showers']
                # Find showers that can fit this door (if Width column exists)
                if 'Width' in showers_df.columns:
                    compatible_showers = showers_df[showers_df['Width'] >= door_width]
                    shower_skus = compatible_showers['Unique ID'].astype(str).tolist()
                    
                    if shower_skus:
                        compatible_products.append({
                            "category": "Showers",
                            "skus": shower_skus
                        })
                    
        # Add similar logic for other categories (Walls, Tub Doors, etc.)
        
        # If no specific compatibility logic matched or no compatible products found,
        # check if there are explicit compatibility columns in the product info
        if not compatible_products:
            # Check for explicitly listed compatible doors
            if 'Compatible Doors' in product_info and pd.notna(product_info['Compatible Doors']):
                compatible_doors = str(product_info['Compatible Doors']).split(',')
                compatible_products.append({
                    "category": "Doors",
                    "skus": [door.strip() for door in compatible_doors]
                })
                
            # Check for explicitly listed compatible walls
            if 'Compatible Walls' in product_info and pd.notna(product_info['Compatible Walls']):
                compatible_walls = str(product_info['Compatible Walls']).split(',')
                compatible_products.append({
                    "category": "Walls", 
                    "skus": [wall.strip() for wall in compatible_walls]
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
