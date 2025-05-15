import os
import pandas as pd
import logging
import glob
import re
import time
from datetime import datetime
from logic import base_compatibility
from logic import bathtub_compatibility
from logic import shower_compatibility
from logic import tubshower_compatibility
from logic import image_handler

# Global flag to indicate whether the data update service is available
data_service_available = False

# Try to import the data update service
try:
    import data_update_service
    data_service_available = True
except ImportError:
    pass  # Keep the data_service_available flag as False

# Configure logging
logger = logging.getLogger(__name__)

def get_fixed_door_type(product_info):
    """
    Get door type using only the approved values (Pivot, Sliding, Bypass)
    ONLY use data from the Excel file without making assumptions
    
    Args:
        product_info (dict): Product information dictionary
        
    Returns:
        str: Door type from the approved set or empty string if not available
    """
    # Only use the Door Type column from the Excel file
    if product_info and "Door Type" in product_info and product_info["Door Type"] is not None:
        door_type = product_info["Door Type"]
        if pd.notna(door_type) and door_type and isinstance(door_type, str) and door_type.strip():
            # If the door type is one of our approved types, return it
            if door_type in ["Pivot", "Sliding", "Bypass"]:
                return door_type
            # If it's another value, return as is
            return door_type.strip()
    
    # If no door type is available, return empty string
    # This ensures we don't make assumptions about product types
    return ""

def load_data():
    """
    Load product data either from the in-memory cache (if data update service is running) 
    or from the /data/ folder as a fallback
    
    Returns:
        dict: Dictionary containing DataFrames of product data, with sheet names as keys
    """
    data = {}
    
    # Try to get data from the data update service first
    global data_service_available
    if data_service_available:
        try:
            # Import locally in case it wasn't available at module load time
            import data_update_service as data_service
            cached_data, update_time = data_service.get_product_data()
            if cached_data:
                logger.info(f"Using in-memory product data from cache (last updated: {update_time})")
                return cached_data
            else:
                logger.warning("In-memory cache is empty, falling back to file-based loading")
        except Exception as e:
            logger.error(f"Error accessing data from update service: {str(e)}. Falling back to file-based loading.")
            data_service_available = False
    
    # Fallback: Load from file system if data service is not available or cache is empty
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
                # Use pd.ExcelFile to get all sheet names, with engine explicitly specified
                try:
                    # First try with openpyxl engine
                    excel = pd.ExcelFile(file_path, engine='openpyxl')
                except Exception as e:
                    logger.warning(f"Failed to read with openpyxl engine, trying xlrd: {str(e)}")
                    # If that fails, try with xlrd engine
                    try:
                        excel = pd.ExcelFile(file_path, engine='xlrd')
                    except Exception as e2:
                        logger.error(f"Failed to read Excel file with all engines: {str(e2)}")
                        continue
                        
                sheet_names = excel.sheet_names
                logger.debug(f"Found sheets: {sheet_names}")
                
                # Load each worksheet into a separate DataFrame
                for sheet_name in sheet_names:
                    try:
                        # Try with openpyxl engine first
                        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                    except Exception:
                        # If that fails, try with xlrd engine
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')
                        except Exception as e2:
                            logger.error(f"Failed to read sheet {sheet_name}: {str(e2)}")
                            continue
                    
                    # Use the sheet name as the key in the data dictionary
                    data[sheet_name] = df
                    logger.debug(f"Loaded worksheet '{sheet_name}' with {len(df)} rows")
                
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
        
        # If data loaded successfully from file and data service is available, 
        # update the in-memory cache
        if data and data_service_available:
            try:
                # Import locally in case it wasn't available at module load time
                import data_update_service as data_service
                # Update the global cache with a copy of the data
                with data_service.data_lock:
                    data_service.product_data_cache = data.copy()
                    data_service.last_update_time = datetime.now()
                logger.info("Updated in-memory cache with data loaded from files")
            except Exception as e:
                logger.error(f"Error updating in-memory cache: {str(e)}")
        
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
    # Import numpy for any potential nan values
    import numpy as np
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
                # Store the exact match from this category
                product_info = product_row.iloc[0].to_dict()
                product_category = category
                
                # Ensure the source product info has the correct SKU
                product_info['Unique ID'] = sku
                
                # Log that we found the product and where
                logger.debug(f"Found product in category: {category}")
                logger.debug(f"Product name: {product_info.get('Product Name', 'Unknown')}")
                
                # Since we found a direct match, stop searching other categories
                break
        
        if product_info is None:
            logger.warning(f"No product found for SKU: {sku}")
            return {"product": None, "compatibles": []}
        
        # Set up the empty results list
        compatible_products = []
        is_bathtub = False
        
        # Call the appropriate compatibility logic based on product category
        if product_category == 'Bathtubs':
            # Use the dedicated bathtub compatibility logic
            logger.debug(f"Using bathtub compatibility logic for SKU: {sku}")
            is_bathtub = True
            
            # Find compatible products for the bathtub
            # This returns a list of categories with already enhanced products
            compatible_products = bathtub_compatibility.find_bathtub_compatibilities(data, product_info)
            
        elif product_category == 'Showers':
            # Use the dedicated shower compatibility logic
            logger.debug(f"Using shower compatibility logic for SKU: {sku}")
            
            # Find compatible products for the shower
            # This returns a list of categories with already enhanced products
            compatible_products = shower_compatibility.find_shower_compatibilities(data, product_info)
            
        elif product_category == 'Tub Showers':
            # Use the dedicated tub shower compatibility logic
            logger.debug(f"Using tub shower compatibility logic for SKU: {sku}")
            
            # Find compatible products for the tub shower
            # This returns a list of categories with already enhanced products
            compatible_products = tubshower_compatibility.find_tubshower_compatibilities(data, product_info)
            
        elif product_category == 'Shower Bases':
            # Use the dedicated shower base compatibility logic
            logger.debug(f"Using shower base compatibility logic for SKU: {sku}")
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
                            # Get the ranking from the door component (if available)
                            ranking_value = 999  # Default high ranking if not specified
                            if "Ranking" in door_info and door_info["Ranking"] is not None:
                                try:
                                    # Make sure we're converting to float properly
                                    ranking_str = str(door_info["Ranking"]).strip()
                                    if ranking_str:
                                        ranking_value = float(ranking_str)
                                        logger.debug(f"Using ranking {ranking_value} for combo {door_sku}|{panel_sku}")
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"Invalid ranking value for {door_sku}: {door_info.get('Ranking')}, error: {str(e)}")
                                    
                            combo_product = {
                                "sku": sku_item,
                                "is_combo": True,
                                "_ranking": ranking_value,  # Internal use only, not sent to frontend
                                "main_product": {
                                    "sku": door_sku,
                                    "name": door_info.get("Product Name", ""),
                                    "image_url": image_handler.generate_image_url(door_info),
                                    "nominal_dimensions": door_info.get("Nominal Dimensions", ""),
                                    "brand": door_info.get("Brand", ""),
                                    "series": door_info.get("Series", ""),
                                    "glass_thickness": door_info.get("Glass Thickness", ""),
                                    "door_type": get_fixed_door_type(door_info),
                                    "max_door_width": door_info.get("Maximum Width", "")
                                },
                                "secondary_product": {
                                    "sku": panel_sku,
                                    "name": panel_info.get("Product Name", ""),
                                    "image_url": image_handler.generate_image_url(panel_info),
                                    "nominal_dimensions": panel_info.get("Nominal Dimensions", ""),
                                    "brand": panel_info.get("Brand", ""),
                                    "series": panel_info.get("Series", ""),
                                    "glass_thickness": panel_info.get("Glass Thickness", "")
                                }
                            }
                            enhanced_skus.append(combo_product)
                    else:
                        product_info = get_product_details(data, sku_item)
                        if product_info:
                            # Get ranking value for non-combo product
                            ranking_value = 999  # Default high ranking if not specified
                            if "Ranking" in product_info and product_info["Ranking"] is not None:
                                try:
                                    # Make sure we're converting to float properly
                                    ranking_str = str(product_info["Ranking"]).strip()
                                    if ranking_str:
                                        ranking_value = float(ranking_str)
                                        logger.debug(f"Using ranking {ranking_value} for product {sku_item}")
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"Invalid ranking value for {sku_item}: {product_info.get('Ranking')}, error: {str(e)}")
                            
                            product_dict = {
                                "sku": sku_item,
                                "is_combo": False,
                                "_ranking": ranking_value,  # Internal use only, not sent to frontend
                                "name": product_info.get("Product Name", "") if product_info.get("Product Name") is not None else "",
                                "image_url": image_handler.generate_image_url(product_info),
                                "nominal_dimensions": product_info.get("Nominal Dimensions", "") if product_info.get("Nominal Dimensions") is not None else "",
                                "brand": product_info.get("Brand", "") if product_info.get("Brand") is not None else "",
                                "series": product_info.get("Series", "") if product_info.get("Series") is not None else "",
                                "glass_thickness": product_info.get("Glass Thickness", "") if product_info.get("Glass Thickness") is not None else "",
                                "door_type": get_fixed_door_type(product_info),
                                "max_door_width": product_info.get("Maximum Width", "") if product_info.get("Maximum Width") is not None else ""
                            }
                            enhanced_skus.append(product_dict)
                
                # Sort products by ranking value (lowest ranking first)
                enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                logger.debug(f"Sorted {len(enhanced_skus)} products by ranking for category {category}")
                
                compatible_products.append({
                    "category": category,
                    "products": enhanced_skus
                })
        
        # BACKWARDS COMPATIBILITY: Find bases/bathtubs compatible with doors
        elif product_category in ['Shower Doors', 'Tub Doors']:
            logger.debug(f"Using backward compatibility logic for door SKU: {sku}")
            
            # Get key door properties
            door_min_width = product_info.get("Minimum Width")
            door_max_width = product_info.get("Maximum Width") 
            door_series = product_info.get("Series")
            door_has_return = product_info.get("Has Return Panel") == "Yes"
            door_family = product_info.get("Family")
            door_type = product_info.get("Type", "").lower()
            
            logger.debug(f"Door properties: Min Width={door_min_width}, Max Width={door_max_width}, Series={door_series}")
            logger.debug(f"Door has return: {door_has_return}, Family: {door_family}, Type: {door_type}")
            
            # Find compatible bathtubs (for Tub Doors)
            if product_category == 'Tub Doors' and 'Bathtubs' in data:
                bathtub_matches = []
                bathtubs_df = data['Bathtubs']
                
                for _, tub in bathtubs_df.iterrows():
                    tub_width = tub.get("Max Door Width")
                    tub_install = tub.get("Installation")
                    tub_series = tub.get("Series")
                    tub_id = str(tub.get("Unique ID", "")).strip()
                    
                    # Match criteria for tub doors
                    if (tub_install == "Alcove" and 
                        pd.notna(tub_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= tub_width <= door_max_width and
                        bathtub_compatibility.series_compatible(tub_series, door_series)):
                        
                        # Format tub data for the frontend
                        tub_data = tub.to_dict()
                        # Remove any NaN values
                        tub_data = {k: v for k, v in tub_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": tub_id,
                            "is_combo": False,
                            "_ranking": tub_data.get("Ranking", 999),
                            "name": tub_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(tub_data),
                            "nominal_dimensions": tub_data.get("Nominal Dimensions", ""),
                            "brand": tub_data.get("Brand", ""),
                            "series": tub_data.get("Series", ""),
                            "max_door_width": tub_data.get("Max Door Width", ""),
                            "installation": tub_data.get("Installation", "")
                        }
                        bathtub_matches.append(product_dict)
                
                # Sort bathtubs by ranking
                if bathtub_matches:
                    bathtub_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Bathtubs",
                        "products": bathtub_matches
                    })
            
            # Find compatible shower bases (for Shower Doors)
            if product_category == 'Shower Doors' and 'Shower Bases' in data:
                base_matches = []
                bases_df = data['Shower Bases']
                
                for _, base in bases_df.iterrows():
                    base_width = base.get("Max Door Width")
                    base_install = str(base.get("Installation", "")).lower()
                    base_series = base.get("Series")
                    base_fit_return = base.get("Fits Return Panel Size")
                    base_id = str(base.get("Unique ID", "")).strip()
                    
                    # Match criteria for alcove installation
                    alcove_match = (
                        "alcove" in base_install and 
                        pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= base_width <= door_max_width and
                        base_compatibility.series_compatible(base_series, door_series)
                    )
                    
                    # Match criteria for corner installation with return panel
                    corner_match = (
                        "corner" in base_install and door_has_return and
                        pd.notna(base_width) and pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= base_width <= door_max_width and
                        base_compatibility.series_compatible(base_series, door_series)
                    )
                    
                    if alcove_match or corner_match:
                        # Format base data for the frontend
                        base_data = base.to_dict()
                        # Remove any NaN values
                        base_data = {k: v for k, v in base_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": base_id,
                            "is_combo": False,
                            "_ranking": base_data.get("Ranking", 999),
                            "name": base_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(base_data),
                            "nominal_dimensions": base_data.get("Nominal Dimensions", ""),
                            "brand": base_data.get("Brand", ""),
                            "series": base_data.get("Series", ""),
                            "max_door_width": base_data.get("Max Door Width", ""),
                            "installation": base_data.get("Installation", "")
                        }
                        base_matches.append(product_dict)
                
                # Sort shower bases by ranking
                if base_matches:
                    base_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Shower Bases",
                        "products": base_matches
                    })
                    
            # Find compatible shower units (for Shower Doors)
            if product_category == 'Shower Doors' and 'Showers' in data:
                shower_matches = []
                showers_df = data['Showers']
                
                for _, shower in showers_df.iterrows():
                    shower_width = shower.get("Max Door Width")
                    shower_height = shower.get("Max Door Height")
                    shower_install = shower.get("Installation")
                    shower_series = shower.get("Series")
                    shower_id = str(shower.get("Unique ID", "")).strip()
                    
                    # Match criteria for alcove shower installations
                    if (
                        shower_install == "Alcove" and
                        pd.notna(shower_width) and pd.notna(shower_height) and
                        pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= shower_width <= door_max_width and
                        shower_compatibility.series_compatible(shower_series, door_series)
                    ):
                        # Format shower data for the frontend
                        shower_data = shower.to_dict()
                        # Remove any NaN values
                        shower_data = {k: v for k, v in shower_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": shower_id,
                            "is_combo": False,
                            "_ranking": shower_data.get("Ranking", 999),
                            "name": shower_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(shower_data),
                            "nominal_dimensions": shower_data.get("Nominal Dimensions", ""),
                            "brand": shower_data.get("Brand", ""),
                            "series": shower_data.get("Series", ""),
                            "max_door_width": shower_data.get("Max Door Width", ""),
                            "max_door_height": shower_data.get("Max Door Height", ""),
                            "installation": shower_data.get("Installation", "")
                        }
                        shower_matches.append(product_dict)
                
                # Sort showers by ranking
                if shower_matches:
                    shower_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Showers",
                        "products": shower_matches
                    })
                    
            # Find compatible tub shower units (for Tub Doors)
            if product_category == 'Tub Doors' and 'Tub Showers' in data:
                tubshower_matches = []
                tubshowers_df = data['Tub Showers']
                
                for _, tubshower in tubshowers_df.iterrows():
                    tubshower_width = tubshower.get("Max Door Width")
                    tubshower_height = tubshower.get("Max Door Height")
                    tubshower_series = tubshower.get("Series")
                    tubshower_id = str(tubshower.get("Unique ID", "")).strip()
                    
                    # Match criteria for tub shower installations
                    if (
                        pd.notna(tubshower_width) and pd.notna(tubshower_height) and
                        pd.notna(door_min_width) and pd.notna(door_max_width) and
                        door_min_width <= tubshower_width <= door_max_width and
                        tubshower_compatibility.series_compatible(tubshower_series, door_series)
                    ):
                        # Format tub shower data for the frontend
                        tubshower_data = tubshower.to_dict()
                        # Remove any NaN values
                        tubshower_data = {k: v for k, v in tubshower_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": tubshower_id,
                            "is_combo": False,
                            "_ranking": tubshower_data.get("Ranking", 999),
                            "name": tubshower_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(tubshower_data),
                            "nominal_dimensions": tubshower_data.get("Nominal Dimensions", ""),
                            "brand": tubshower_data.get("Brand", ""),
                            "series": tubshower_data.get("Series", ""),
                            "max_door_width": tubshower_data.get("Max Door Width", ""),
                            "max_door_height": tubshower_data.get("Max Door Height", "")
                        }
                        tubshower_matches.append(product_dict)
                
                # Sort tub showers by ranking
                if tubshower_matches:
                    tubshower_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Tub Showers",
                        "products": tubshower_matches
                    })
                    
        # BACKWARDS COMPATIBILITY: Find bases/bathtubs compatible with walls
        elif product_category == 'Walls':
            logger.debug(f"Using backward compatibility logic for wall SKU: {sku}")
            
            # Get key wall properties
            wall_type = str(product_info.get("Type", "")).lower()
            wall_brand = product_info.get("Brand")
            wall_family = product_info.get("Family")
            wall_series = product_info.get("Series")
            wall_nominal = product_info.get("Nominal Dimensions")
            wall_length = product_info.get("Length")
            wall_width = product_info.get("Width")
            wall_cut = product_info.get("Cut to Size")
            
            logger.debug(f"Wall properties: Type={wall_type}, Brand={wall_brand}, Family={wall_family}, Series={wall_series}")
            logger.debug(f"Wall dimensions: Nominal={wall_nominal}, Length={wall_length}, Width={wall_width}, Cut to Size={wall_cut}")
            
            # Find compatible bathtubs (for bathtub walls)
            if 'tub' in wall_type and 'Bathtubs' in data:
                bathtub_matches = []
                bathtubs_df = data['Bathtubs']
                
                for _, tub in bathtubs_df.iterrows():
                    tub_nominal = tub.get("Nominal Dimensions")
                    tub_length = tub.get("Length")
                    tub_width = tub.get("Width")
                    tub_brand = tub.get("Brand")
                    tub_family = tub.get("Family")
                    tub_series = tub.get("Series")
                    tub_id = str(tub.get("Unique ID", "")).strip()
                    
                    # Check brand/family compatibility
                    brand_match = bathtub_compatibility.bathtub_brand_family_match(
                        tub_brand, tub_family, wall_brand, wall_family
                    )
                    
                    # Check series compatibility
                    series_match = bathtub_compatibility.series_compatible(tub_series, wall_series)
                    
                    # Skip if no brand or series match
                    if not (brand_match and series_match):
                        continue
                    
                    # Match criteria - exact nominal dimensions
                    nominal_match = False
                    if wall_cut != "Yes" and tub_nominal == wall_nominal:
                        nominal_match = True
                    
                    # Match criteria - cut to size walls
                    cut_match = False
                    if (wall_cut == "Yes" and pd.notna(tub_length) and pd.notna(tub_width) and
                        pd.notna(wall_length) and pd.notna(wall_width) and
                        wall_length >= tub_length and wall_width >= tub_width):
                        cut_match = True
                    
                    if nominal_match or cut_match:
                        # Format tub data for the frontend
                        tub_data = tub.to_dict()
                        # Remove any NaN values
                        tub_data = {k: v for k, v in tub_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": tub_id,
                            "is_combo": False,
                            "_ranking": tub_data.get("Ranking", 999),
                            "name": tub_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(tub_data),
                            "nominal_dimensions": tub_data.get("Nominal Dimensions", ""),
                            "brand": tub_data.get("Brand", ""),
                            "series": tub_data.get("Series", ""),
                            "max_door_width": tub_data.get("Max Door Width", ""),
                            "installation": tub_data.get("Installation", "")
                        }
                        bathtub_matches.append(product_dict)
                
                # Sort bathtubs by ranking
                if bathtub_matches:
                    bathtub_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Bathtubs",
                        "products": bathtub_matches
                    })
            
            # Find compatible shower bases (for shower walls)
            if 'shower' in wall_type and 'Shower Bases' in data:
                base_matches = []
                bases_df = data['Shower Bases']
                
                for _, base in bases_df.iterrows():
                    base_nominal = base.get("Nominal Dimensions")
                    base_length = base.get("Length")
                    base_width_actual = base.get("Width")
                    base_brand = base.get("Brand")
                    base_family = base.get("Family")
                    base_series = base.get("Series")
                    base_install = str(base.get("Installation", "")).lower()
                    base_id = str(base.get("Unique ID", "")).strip()
                    
                    # Check installation type compatibility
                    if 'alcove' in wall_type and 'alcove' not in base_install:
                        continue
                    if 'corner' in wall_type and 'corner' not in base_install:
                        continue
                    
                    # Check brand family compatibility
                    brand_match = base_compatibility.brand_family_match(
                        base_brand, base_family, wall_brand, wall_family
                    )
                    
                    # Check series compatibility
                    series_match = base_compatibility.series_compatible(base_series, wall_series)
                    
                    # Skip if no brand or series match
                    if not (brand_match and series_match):
                        continue
                    
                    # Match criteria - exact nominal dimensions
                    nominal_match = False
                    if wall_cut != "Yes" and base_nominal == wall_nominal:
                        nominal_match = True
                    
                    # Match criteria - cut to size walls
                    cut_match = False
                    if (wall_cut == "Yes" and pd.notna(base_length) and pd.notna(base_width_actual) and
                        pd.notna(wall_length) and pd.notna(wall_width) and
                        wall_length >= base_length and wall_width >= base_width_actual):
                        cut_match = True
                    
                    if nominal_match or cut_match:
                        # Format base data for the frontend
                        base_data = base.to_dict()
                        # Remove any NaN values
                        base_data = {k: v for k, v in base_data.items() if pd.notna(v)}
                        
                        product_dict = {
                            "sku": base_id,
                            "is_combo": False,
                            "_ranking": base_data.get("Ranking", 999),
                            "name": base_data.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(base_data),
                            "nominal_dimensions": base_data.get("Nominal Dimensions", ""),
                            "brand": base_data.get("Brand", ""),
                            "series": base_data.get("Series", ""),
                            "max_door_width": base_data.get("Max Door Width", ""),
                            "installation": base_data.get("Installation", "")
                        }
                        base_matches.append(product_dict)
                
                # Sort shower bases by ranking
                if base_matches:
                    base_matches.sort(key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Shower Bases",
                        "products": base_matches
                    })
            
        # Additional categories can be added here with their own dedicated modules
        
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
                        # Get ranking value for explicitly listed compatible product
                        ranking_value = 999  # Default high ranking if not specified
                        if "Ranking" in door_info and door_info["Ranking"] is not None:
                            try:
                                # Make sure we're converting to float properly
                                ranking_str = str(door_info["Ranking"]).strip()
                                if ranking_str:
                                    ranking_value = float(ranking_str)
                                    logger.debug(f"Using ranking {ranking_value} for door {door_sku}")
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Invalid ranking value for {door_sku}: {door_info.get('Ranking')}, error: {str(e)}")
                                
                        enhanced_skus.append({
                            "sku": door_sku,
                            "is_combo": False,
                            "_ranking": ranking_value,  # Internal use only, not sent to frontend
                            "name": door_info.get("Product Name", "") if door_info.get("Product Name") is not None else "",
                            "image_url": image_handler.generate_image_url(door_info),
                            "nominal_dimensions": door_info.get("Nominal Dimensions", "") if door_info.get("Nominal Dimensions") is not None else "",
                            "brand": door_info.get("Brand", "") if door_info.get("Brand") is not None else "",
                            "series": door_info.get("Series", "") if door_info.get("Series") is not None else "",
                            "glass_thickness": door_info.get("Glass Thickness", "") if door_info.get("Glass Thickness") is not None else "",
                            "door_type": get_fixed_door_type(door_info),
                            "max_door_width": door_info.get("Maximum Width", "") if door_info.get("Maximum Width") is not None else ""
                        })
                
                if enhanced_skus:
                    # Sort products by ranking value (lowest ranking first)
                    enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                    logger.debug(f"Sorted {len(enhanced_skus)} products by ranking for Doors category")
                    
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
                        # Get ranking value for walls
                        ranking_value = 999  # Default high ranking if not specified
                        if "Ranking" in wall_info and wall_info["Ranking"] is not None:
                            try:
                                # Make sure we're converting to float properly
                                ranking_str = str(wall_info["Ranking"]).strip()
                                if ranking_str:
                                    ranking_value = float(ranking_str)
                                    logger.debug(f"Using ranking {ranking_value} for wall {wall_sku}")
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Invalid ranking value for wall {wall_sku}: {wall_info.get('Ranking')}, error: {str(e)}")
                                
                        enhanced_skus.append({
                            "sku": wall_sku,
                            "is_combo": False,
                            "_ranking": ranking_value,  # Internal use only, not sent to frontend
                            "name": wall_info.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(wall_info),
                            "nominal_dimensions": wall_info.get("Nominal Dimensions", ""),
                            "brand": wall_info.get("Brand", ""),
                            "series": wall_info.get("Series", "")
                        })
                
                if enhanced_skus:
                    # Sort products by ranking value (lowest ranking first)
                    enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                    logger.debug(f"Sorted {len(enhanced_skus)} products by ranking for Walls category")
                    
                    compatible_products.append({
                        "category": "Walls", 
                        "products": enhanced_skus
                    })
        
        # THIS IS THE ROOT CAUSE FIX: Always get the correct original product information 
        # before proceeding with compatibility checks
        
        # Before finding compatibles, preserve the original source product information
        # so it doesn't get overwritten during the compatibility search process
        logger.debug(f"Creating source product details for SKU: {sku} in category: {product_category}")
        
        # Make a separate request to get the accurate source product info
        # This ensures we always use the right product information
        original_product_info = None
        
        # Search all worksheets for the exact SKU to get the correct product information
        # This is a comprehensive solution to ensure we get the right product details 
        # regardless of which worksheet it comes from
        for sheet_name, df in data.items():
            if 'Unique ID' in df.columns:
                # Case-insensitive search for the SKU
                matching_rows = df[df['Unique ID'].astype(str).str.upper() == sku.upper()]
                if not matching_rows.empty:
                    original_product_info = matching_rows.iloc[0].to_dict()
                    logger.debug(f"Found original product in {sheet_name}: {original_product_info.get('Product Name', 'Unknown')}")
                    # Update the category if it's different
                    product_category = sheet_name
                    break  # Stop once we find a direct match

        # If we couldn't find the original product in any category, use what we have
        if original_product_info is None:
            original_product_info = product_info if product_info is not None else {}
            logger.debug(f"Using found product info: {original_product_info.get('Product Name', 'Unknown')}")
            
        # Create a source product with the correct information
        source_product = {
            "sku": sku,
            "category": product_category,
            "name": original_product_info.get("Product Name", "") if original_product_info.get("Product Name") is not None else "",
            "image_url": image_handler.generate_image_url(original_product_info),
            "nominal_dimensions": original_product_info.get("Nominal Dimensions", "") if original_product_info.get("Nominal Dimensions") is not None else "",
            "installation": original_product_info.get("Installation", "") if original_product_info.get("Installation") is not None else "",
            "brand": original_product_info.get("Brand", "") if original_product_info.get("Brand") is not None else "",
            "series": original_product_info.get("Series", "") if original_product_info.get("Series") is not None else "",
            "family": original_product_info.get("Family", "") if original_product_info.get("Family") is not None else "",
        }
        
        # Handle max_door_width - this field has different column names in different sheets
        # For Shower Bases, Bathtubs, Showers, and Tub Showers, use "Max Door Width", for doors use "Maximum Width"
        if product_category in ["Bathtubs", "Shower Bases", "Showers", "Tub Showers"]:
            source_product["max_door_width"] = original_product_info.get("Max Door Width", "") if original_product_info.get("Max Door Width") is not None else ""
            logger.debug(f"Using Max Door Width from {product_category}: {source_product['max_door_width']}")
        else:
            source_product["max_door_width"] = original_product_info.get("Maximum Width", "") if original_product_info.get("Maximum Width") is not None else ""
            logger.debug(f"Using Maximum Width from {product_category}: {source_product['max_door_width']}")
            
        # Handle max_door_height for Showers and Tub Showers
        if product_category in ["Showers", "Tub Showers"]:
            source_product["max_door_height"] = original_product_info.get("Max Door Height", "") if original_product_info.get("Max Door Height") is not None else ""
            logger.debug(f"Using Max Door Height from {product_category}: {source_product.get('max_door_height', 'N/A')}")
            
        logger.debug(f"Source product name (final): {source_product['name']}")
        
        # If this is a bathtub, use the bathtub compatibility results
        if is_bathtub:
            logger.debug(f"Using bathtub compatibility results for SKU: {sku}")
            # Use the compatibility results from the bathtub-specific function
            return {
                "product": source_product,
                "compatibles": compatible_products
            }
        
        # For all other product types (shower bases, etc.), process as usual
        # Sort each category's products by ranking (lowest to highest)
        # And remove the internal _ranking field before sending to frontend
        for category in compatible_products:
            if "products" in category and category["products"]:
                # First log the products before sorting (for debugging)
                logger.debug(f"Products in {category['category']} before sorting:")
                for idx, product in enumerate(category["products"]):
                    if product.get("is_combo", False):
                        sku_display = f"{product['main_product']['sku']}|{product['secondary_product']['sku']}"
                    else:
                        sku_display = product.get('sku', 'Unknown')
                        
                    ranking = product.get("_ranking", 999)
                    name = product.get('name', '')
                    if not name and product.get("is_combo", False):
                        name = product.get('main_product', {}).get('name', '')
                        
                    logger.debug(f"  {idx}: {sku_display} ({name}) - Ranking: {ranking}")
                
                # Sort products based on the _ranking field (ascending order)
                # First ensure all ranking values are properly converted to float
                for product in category["products"]:
                    if "_ranking" in product:
                        try:
                            original_val = product["_ranking"]
                            product["_ranking"] = float(product["_ranking"])
                            # Log if conversion changes the value
                            if original_val != product["_ranking"]:
                                logger.debug(f"Converted ranking from {original_val} to {product['_ranking']}")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Invalid ranking value: {product['_ranking']}, error: {str(e)}")
                            product["_ranking"] = 999
                
                # Now sort with proper numeric comparison
                category["products"].sort(key=lambda p: p.get("_ranking", 999))
                
                # Log the products after sorting (for debugging)
                logger.debug(f"Products in {category['category']} after sorting:")
                for idx, product in enumerate(category["products"]):
                    if product.get("is_combo", False):
                        sku_display = f"{product['main_product']['sku']}|{product['secondary_product']['sku']}"
                    else:
                        sku_display = product.get('sku', 'Unknown')
                        
                    ranking = product.get("_ranking", 999)
                    name = product.get('name', '')
                    if not name and product.get("is_combo", False):
                        name = product.get('main_product', {}).get('name', '')
                        
                    logger.debug(f"  {idx}: {sku_display} ({name}) - Ranking: {ranking}")
                
                # Remove the _ranking field from each product as it's for internal use only
                for product in category["products"]:
                    if "_ranking" in product:
                        del product["_ranking"]
        
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
        logger.debug(f"Looking for product details for SKU: {sku}")
        
        for category, df in data.items():
            # Skip any dataframes without a Unique ID column
            if 'Unique ID' not in df.columns:
                continue
                
            # Find the product in this category
            # Convert everything to string and uppercase for case-insensitive comparison
            product_row = df[df['Unique ID'].astype(str).str.upper() == sku.upper()]
            
            if not product_row.empty:
                # Convert to dict and clean up NaN values
                product_info = product_row.iloc[0].to_dict()
                
                # Clean up NaN values in the dictionary
                for key, value in product_info.items():
                    if pd.isna(value):
                        product_info[key] = None
                
                # Add the category to the product info
                product_info['_source_category'] = category
                
                logger.debug(f"Found product in {category}: {product_info.get('Product Name', 'Unknown')}")
                return product_info
                
        logger.debug(f"No product found for SKU: {sku}")
        return None
    except Exception as e:
        logger.error(f"Error in get_product_details: {str(e)}")
        return None

# Note: This placeholder implementation should be replaced with the actual
# compatibility logic from the existing scripts when they are provided.
# The user will need to paste their existing compatibility scripts into this file
# or create additional modules in the logic directory.
