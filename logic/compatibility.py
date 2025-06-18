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
from logic import blacklist_helper
from logic import whitelist_helper

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


def find_tub_screen_compatibilities(data, screen_info):
    """
    Find compatible bathtubs for a tub screen
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        screen_info (dict): Dictionary containing tub screen product information
        
    Returns:
        list: List of dictionaries containing category and compatible products
    """
    try:
        compatible_products = []
        matching_bathtubs = []
        
        screen_fixed_panel_width = screen_info.get("Fixed Panel Width")
        screen_series = screen_info.get("Series")
        screen_brand = screen_info.get("Brand")
        
        logger.debug(f"Finding bathtubs compatible with tub screen: {screen_info.get('Unique ID')}")
        logger.debug(f"Screen Fixed Panel Width: {screen_fixed_panel_width}")
        logger.debug(f"Screen Series: {screen_series}")
        
        if 'Bathtubs' in data and pd.notna(screen_fixed_panel_width):
            bathtubs_df = data['Bathtubs']
            logger.debug(f"Checking {len(bathtubs_df)} bathtubs for compatibility")
            
            try:
                screen_width_num = float(screen_fixed_panel_width)
                logger.debug(f"Screen fixed panel width as number: {screen_width_num}")
                
                for _, bathtub in bathtubs_df.iterrows():
                    bathtub_id = str(bathtub.get("Unique ID", "")).strip()
                    bathtub_name = bathtub.get("Product Name", "")
                    bathtub_max_door_width = bathtub.get("Max Door Width")
                    bathtub_series = bathtub.get("Series")
                    
                    logger.debug(f"  Checking bathtub: {bathtub_id} - {bathtub_name}")
                    logger.debug(f"    Max Door Width: {bathtub_max_door_width}")
                    
                    if pd.notna(bathtub_max_door_width):
                        try:
                            bathtub_width_num = float(bathtub_max_door_width)
                            width_difference = bathtub_width_num - screen_width_num
                            
                            logger.debug(f"    Width difference: {bathtub_width_num} - {screen_width_num} = {width_difference}")
                            
                            # Check compatibility: Max Door Width - Fixed Panel Width > 22
                            from logic.bathtub_compatibility import series_compatible
                            bathtub_compatible = (
                                width_difference > 22 and
                                series_compatible(bathtub_series, screen_series)
                            )
                            
                            logger.debug(f"    Bathtub compatible: {bathtub_compatible}")
                            logger.debug(f"    Series match: {series_compatible(bathtub_series, screen_series)}")
                            
                            if bathtub_compatible and bathtub_id:
                                bathtub_product = {
                                    "sku": bathtub_id,
                                    "name": bathtub.get("Product Name", ""),
                                    "brand": bathtub.get("Brand", ""),
                                    "series": bathtub.get("Series", ""),
                                    "category": "Bathtubs",
                                    "image_url": bathtub.get("Image URL", ""),
                                    "product_page_url": bathtub.get("Product Page URL", ""),
                                    "_ranking": bathtub.get("Ranking", 999),
                                    "is_combo": False,
                                    "max_door_width": bathtub_max_door_width
                                }
                                matching_bathtubs.append(bathtub_product)
                                logger.debug(f"    ✓ Added bathtub {bathtub_id} to matching bathtubs")
                        
                        except (ValueError, TypeError) as e:
                            logger.debug(f"    Error converting bathtub measurements to numbers: {e}")
                            continue
                    else:
                        logger.debug(f"    Missing Max Door Width - skipping")
                        
            except (ValueError, TypeError) as e:
                logger.debug(f"Error converting screen measurements to numbers: {e}")
                return []
        
        if matching_bathtubs:
            # Sort the bathtubs by ranking
            sorted_bathtubs = sorted(matching_bathtubs, key=lambda x: x.get('_ranking', 999))
            logger.debug(f"Adding {len(sorted_bathtubs)} bathtubs to results")
            for bathtub in sorted_bathtubs[:3]:  # Log first few bathtubs
                logger.debug(f"  Bathtub: {bathtub.get('sku')} - {bathtub.get('name')}")
            compatible_products.append({"category": "Bathtubs", "products": sorted_bathtubs})
        
        logger.debug(f"Tub screen compatibility results: {len(matching_bathtubs)} bathtubs found")
        return compatible_products
        
    except Exception as e:
        import traceback
        logger.error(f"Error in find_tub_screen_compatibilities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def find_shower_screen_compatibilities(data, screen_info):
    """
    Find compatible shower bases for a shower screen
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        screen_info (dict): Dictionary containing shower screen product information
        
    Returns:
        list: List of dictionaries containing category and compatible products
    """
    try:
        compatible_products = []
        matching_bases = []
        
        screen_fixed_panel_width = screen_info.get("Fixed Panel Width")
        screen_series = screen_info.get("Series")
        screen_brand = screen_info.get("Brand")
        
        logger.debug(f"Finding bases compatible with screen: {screen_info.get('Unique ID')}")
        logger.debug(f"Screen Fixed Panel Width: {screen_fixed_panel_width}")
        logger.debug(f"Screen Series: {screen_series}")
        
        if 'Shower Bases' in data and pd.notna(screen_fixed_panel_width):
            bases_df = data['Shower Bases']
            logger.debug(f"Checking {len(bases_df)} shower bases for compatibility")
            
            try:
                screen_width_num = float(screen_fixed_panel_width)
                logger.debug(f"Screen fixed panel width as number: {screen_width_num}")
                
                for _, base in bases_df.iterrows():
                    base_id = str(base.get("Unique ID", "")).strip()
                    base_name = base.get("Product Name", "")
                    base_max_door_width = base.get("Max Door Width")
                    base_series = base.get("Series")
                    base_install = str(base.get("Installation", "")).lower()
                    
                    logger.debug(f"  Checking base: {base_id} - {base_name}")
                    logger.debug(f"    Max Door Width: {base_max_door_width}")
                    logger.debug(f"    Installation: {base_install}")
                    
                    if pd.notna(base_max_door_width):
                        try:
                            base_width_num = float(base_max_door_width)
                            width_difference = base_width_num - screen_width_num
                            
                            logger.debug(f"    Width difference: {base_width_num} - {screen_width_num} = {width_difference}")
                            
                            # Check compatibility: Max Door Width - Fixed Panel Width > 22
                            # Compatible with both Alcove and Corner bases
                            from logic.base_compatibility import series_compatible
                            base_compatible = (
                                width_difference > 22 and
                                series_compatible(base_series, screen_series) and
                                ("alcove" in base_install or "corner" in base_install)
                            )
                            
                            logger.debug(f"    Base compatible: {base_compatible}")
                            logger.debug(f"    Series match: {series_compatible(base_series, screen_series)}")
                            logger.debug(f"    Installation type valid: {'alcove' in base_install or 'corner' in base_install}")
                            
                            if base_compatible and base_id:
                                base_product = {
                                    "sku": base_id,
                                    "name": base.get("Product Name", ""),
                                    "brand": base.get("Brand", ""),
                                    "series": base.get("Series", ""),
                                    "category": "Shower Bases",
                                    "image_url": base.get("Image URL", ""),
                                    "product_page_url": base.get("Product Page URL", ""),
                                    "_ranking": base.get("Ranking", 999),
                                    "is_combo": False,
                                    "max_door_width": base_max_door_width,
                                    "installation": base.get("Installation", "")
                                }
                                matching_bases.append(base_product)
                                logger.debug(f"    ✓ Added base {base_id} to matching bases")
                        
                        except (ValueError, TypeError) as e:
                            logger.debug(f"    Error converting base measurements to numbers: {e}")
                            continue
                    else:
                        logger.debug(f"    Missing Max Door Width - skipping")
                        
            except (ValueError, TypeError) as e:
                logger.debug(f"Error converting screen measurements to numbers: {e}")
                return []
        
        if matching_bases:
            # Sort the bases by ranking
            sorted_bases = sorted(matching_bases, key=lambda x: x.get('_ranking', 999))
            logger.debug(f"Adding {len(sorted_bases)} shower bases to results")
            for base in sorted_bases[:3]:  # Log first few bases
                logger.debug(f"  Base: {base.get('sku')} - {base.get('name')}")
            compatible_products.append({"category": "Shower Bases", "products": sorted_bases})
        
        logger.debug(f"Screen compatibility results: {len(matching_bases)} bases found")
        return compatible_products
        
    except Exception as e:
        import traceback
        logger.error(f"Error in find_shower_screen_compatibilities: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def get_fixed_door_type(product_info):
    """
    Get door type using only the approved values (Pivot, Sliding, Bypass)
    ONLY use data from the Excel file without making assumptions

    Args:
        product_info (dict): Product information dictionary

    Returns:
        str: Door type from the approved set or empty string if not available
    """
    # Check for "Door Type" column first
    if product_info and ("Door Type" in product_info
                         or "Door  Type" in product_info) and (
                             product_info.get("Door Type") is not None
                             or product_info.get("Door  Type") is not None):
        door_type = product_info.get("Door Type") or product_info.get(
            "Door  Type")
        if pd.notna(door_type) and door_type and isinstance(
                door_type, str) and door_type.strip():
            # If the door type is one of our approved types, return it
            if door_type in ["Pivot", "Sliding", "Bypass"]:
                return door_type
            # If it's another value, return as is
            return door_type.strip()

    # Try "Type" column as fallback for Tub Doors
    if product_info and "Type" in product_info and product_info[
            "Type"] is not None:
        door_type = product_info["Type"]
        if pd.notna(door_type) and door_type and isinstance(
                door_type, str) and door_type.strip():
            # Convert to an approved type if possible
            door_type_lower = door_type.lower().strip()
            if "pivot" in door_type_lower:
                return "Pivot"
            elif "sliding" in door_type_lower:
                return "Sliding"
            elif "bypass" in door_type_lower:
                return "Bypass"
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
                logger.info(
                    f"Using in-memory product data from cache (last updated: {update_time})"
                )
                return cached_data
            else:
                logger.warning(
                    "In-memory cache is empty, falling back to file-based loading"
                )
        except Exception as e:
            logger.error(
                f"Error accessing data from update service: {str(e)}. Falling back to file-based loading."
            )
            data_service_available = False

    # Fallback: Load from file system if data service is not available or cache is empty
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'data')
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
                    logger.warning(
                        f"Failed to read with openpyxl engine, trying xlrd: {str(e)}"
                    )
                    # If that fails, try with xlrd engine
                    try:
                        excel = pd.ExcelFile(file_path, engine='xlrd')
                    except Exception as e2:
                        logger.error(
                            f"Failed to read Excel file with all engines: {str(e2)}"
                        )
                        continue

                sheet_names = excel.sheet_names
                logger.debug(f"Found sheets: {sheet_names}")

                # Load each worksheet into a separate DataFrame
                for sheet_name in sheet_names:
                    try:
                        # Try with openpyxl engine first
                        df = pd.read_excel(file_path,
                                           sheet_name=sheet_name,
                                           engine='openpyxl')
                    except Exception:
                        # If that fails, try with xlrd engine
                        try:
                            df = pd.read_excel(file_path,
                                               sheet_name=sheet_name,
                                               engine='xlrd')
                        except Exception as e2:
                            logger.error(
                                f"Failed to read sheet {sheet_name}: {str(e2)}"
                            )
                            continue

                    # Use the sheet name as the key in the data dictionary
                    data[sheet_name] = df
                    logger.debug(
                        f"Loaded worksheet '{sheet_name}' with {len(df)} rows")

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
                logger.info(
                    "Updated in-memory cache with data loaded from files")
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
            product_row = df[df[id_column].astype(str).str.upper() ==
                             sku.upper()]

            if not product_row.empty:
                # Store the exact match from this category
                product_info = product_row.iloc[0].to_dict()
                product_category = category

                # Ensure the source product info has the correct SKU
                product_info['Unique ID'] = sku

                # Log that we found the product and where
                logger.debug(f"Found product in category: {category}")
                logger.debug(
                    f"Product name: {product_info.get('Product Name', 'Unknown')}"
                )

                # Since we found a direct match, stop searching other categories
                break

        if product_info is None:
            logger.warning(f"No product found for SKU: {sku}")
            return {"product": None, "compatibles": []}

        # Set up the empty results list
        compatible_products = []
        incompatibility_reasons = {}
        is_bathtub = False

        # Call the appropriate compatibility logic based on product category
        if product_category == 'Bathtubs':
            # Use the dedicated bathtub compatibility logic
            logger.debug(f"Using bathtub compatibility logic for SKU: {sku}")
            is_bathtub = True

            # Find compatible products for the bathtub
            # This returns a list of categories with already enhanced products
            compatible_products = bathtub_compatibility.find_bathtub_compatibilities(
                data, product_info)

        elif product_category == 'Showers':
            # Use the dedicated shower compatibility logic
            logger.debug(f"Using shower compatibility logic for SKU: {sku}")

            # Find compatible products for the shower
            # This returns a list of categories with already enhanced products
            compatible_products = shower_compatibility.find_shower_compatibilities(
                data, product_info)

        elif product_category == 'Tub Showers':
            # Use the dedicated tub shower compatibility logic
            logger.debug(
                f"Using tub shower compatibility logic for SKU: {sku}")

            # Find compatible products for the tub shower
            # This returns a list of categories with already enhanced products
            compatible_products = tubshower_compatibility.find_tubshower_compatibilities(
                data, product_info)

        elif product_category == 'Tub Screens':
            # Find compatible bathtubs for the tub screen
            logger.debug(f"Using tub screen reverse compatibility logic for SKU: {sku}")
            compatible_categories = find_tub_screen_compatibilities(data, product_info)
            
            # Enhance the results with additional product details
            for category_info in compatible_categories:
                category = category_info["category"]
                enhanced_skus = []
                
                # Handle the products format
                if "products" in category_info:
                    products_list = category_info["products"]
                else:
                    products_list = category_info.get("skus", [])
                
                for sku_item in products_list:
                    # Handle product dictionaries (should already be enhanced)
                    if isinstance(sku_item, dict):
                        enhanced_skus.append(sku_item)
                        continue
                    
                    # Handle string SKUs (shouldn't happen with our implementation but just in case)
                    sku_details = get_product_details(data, sku_item)
                    if sku_details:
                        enhanced_product = {
                            "sku": sku_item,
                            "name": sku_details.get("Product Name", ""),
                            "brand": sku_details.get("Brand", ""),
                            "series": sku_details.get("Series", ""),
                            "category": category,
                            "image_url": sku_details.get("Image URL", ""),
                            "product_page_url": sku_details.get("Product Page URL", ""),
                            "_ranking": sku_details.get("Ranking", 999),
                            "is_combo": False
                        }
                        enhanced_skus.append(enhanced_product)
                
                # Sort by ranking and add to results
                enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                compatible_products.append({
                    "category": category,
                    "products": enhanced_skus
                })

        elif product_category == 'Shower Screens':
            # Find compatible shower bases for the shower screen
            logger.debug(f"Using shower screen reverse compatibility logic for SKU: {sku}")
            compatible_categories = find_shower_screen_compatibilities(data, product_info)
            
            # Enhance the results with additional product details
            for category_info in compatible_categories:
                category = category_info["category"]
                enhanced_skus = []
                
                # Handle the products format
                if "products" in category_info:
                    products_list = category_info["products"]
                else:
                    products_list = category_info.get("skus", [])
                
                for sku_item in products_list:
                    # Handle product dictionaries (should already be enhanced)
                    if isinstance(sku_item, dict):
                        enhanced_skus.append(sku_item)
                        continue
                    
                    # Handle string SKUs (shouldn't happen with our implementation but just in case)
                    sku_details = get_product_details(data, sku_item)
                    if sku_details:
                        enhanced_product = {
                            "sku": sku_item,
                            "name": sku_details.get("Product Name", ""),
                            "brand": sku_details.get("Brand", ""),
                            "series": sku_details.get("Series", ""),
                            "category": category,
                            "image_url": sku_details.get("Image URL", ""),
                            "product_page_url": sku_details.get("Product Page URL", ""),
                            "_ranking": sku_details.get("Ranking", 999),
                            "is_combo": False
                        }
                        enhanced_skus.append(enhanced_product)
                
                # Sort by ranking and add to results
                enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                compatible_products.append({
                    "category": category,
                    "products": enhanced_skus
                })

        elif product_category == 'Shower Bases':
            # Use the dedicated shower base compatibility logic
            logger.debug(
                f"Using shower base compatibility logic for SKU: {sku}")
            compatible_categories = base_compatibility.find_base_compatibilities(
                data, product_info)
            logger.info(f"Base compatibility returned {len(compatible_categories)} items: {[item.get('category') for item in compatible_categories]}")

            # Separate incompatibility reasons from product categories
            shower_base_incompatibility_reasons = {}
            
            # Enhance the results with additional product details
            logger.info(f"Processing {len(compatible_categories)} categories from base compatibility")
            for category_info in compatible_categories:
                category = category_info["category"]
                logger.info(f"Processing category: {category}, keys: {list(category_info.keys())}")
                
                # Handle incompatibility reasons
                if "reason" in category_info:
                    reason = category_info["reason"]
                    logger.info(f"Found incompatibility reason for {category}: {reason}")
                    shower_base_incompatibility_reasons[category] = reason
                    incompatibility_reasons[category] = reason
                    continue
                
                enhanced_skus = []

                # Handle both old format (with "skus") and new format (with "products")
                if "products" in category_info:
                    products_list = category_info["products"]
                else:
                    products_list = category_info.get("skus", [])
                
                for sku_item in products_list:
                    # Handle both product dictionaries (new format) and SKU strings (old format)
                    if isinstance(sku_item, dict):
                        # New format: sku_item is already a product dictionary
                        enhanced_skus.append(sku_item)
                        continue
                    
                    # Old format: sku_item is a string (SKU)
                    # Check if this is a combined SKU (door + return panel)
                    if "|" in sku_item:
                        door_sku, panel_sku = sku_item.split("|")
                        door_info = get_product_details(data, door_sku)
                        panel_info = get_product_details(data, panel_sku)

                        if door_info and panel_info:
                            # Get the ranking from the door component (if available)
                            ranking_value = 999  # Default high ranking if not specified
                            if "Ranking" in door_info and door_info[
                                    "Ranking"] is not None:
                                try:
                                    # Make sure we're converting to float properly
                                    ranking_str = str(
                                        door_info["Ranking"]).strip()
                                    if ranking_str:
                                        ranking_value = float(ranking_str)
                                        logger.debug(
                                            f"Using ranking {ranking_value} for combo {door_sku}|{panel_sku}"
                                        )
                                except (ValueError, TypeError) as e:
                                    logger.debug(
                                        f"Invalid ranking value for {door_sku}: {door_info.get('Ranking')}, error: {str(e)}"
                                    )

                            combo_product = {
                                "sku": sku_item,
                                "is_combo": True,
                                "_ranking":
                                ranking_value,  # Internal use only, not sent to frontend
                                "main_product": {
                                    "sku":
                                    door_sku,
                                    "name":
                                    door_info.get("Product Name", ""),
                                    "image_url":
                                    image_handler.generate_image_url(
                                        door_info),
                                    "nominal_dimensions":
                                    door_info.get("Nominal Dimensions", ""),
                                    "brand":
                                    door_info.get("Brand", ""),
                                    "series":
                                    door_info.get("Series", ""),
                                    "glass_thickness":
                                    door_info.get("Glass Thickness", ""),
                                    "door_type":
                                    get_fixed_door_type(door_info),
                                    "max_door_width":
                                    door_info.get("Maximum Width", ""),
                                    "material":
                                    door_info.get("Material", ""),
                                    "product_page_url":
                                    door_info.get("Product Page URL", "")
                                },
                                "secondary_product": {
                                    "sku":
                                    panel_sku,
                                    "name":
                                    panel_info.get("Product Name", ""),
                                    "image_url":
                                    image_handler.generate_image_url(
                                        panel_info),
                                    "nominal_dimensions":
                                    panel_info.get("Nominal Dimensions", ""),
                                    "brand":
                                    panel_info.get("Brand", ""),
                                    "series":
                                    panel_info.get("Series", ""),
                                    "glass_thickness":
                                    panel_info.get("Glass Thickness", ""),
                                    "material":
                                    panel_info.get("Material", ""),
                                    "product_page_url":
                                    panel_info.get("Product Page URL", "")
                                }
                            }
                            enhanced_skus.append(combo_product)
                    else:
                        product_info = get_product_details(data, sku_item)
                        if product_info:
                            # Get ranking value for non-combo product
                            ranking_value = 999  # Default high ranking if not specified
                            if "Ranking" in product_info and product_info[
                                    "Ranking"] is not None:
                                try:
                                    # Make sure we're converting to float properly
                                    ranking_str = str(
                                        product_info["Ranking"]).strip()
                                    if ranking_str:
                                        ranking_value = float(ranking_str)
                                        logger.debug(
                                            f"Using ranking {ranking_value} for product {sku_item}"
                                        )
                                except (ValueError, TypeError) as e:
                                    logger.debug(
                                        f"Invalid ranking value for {sku_item}: {product_info.get('Ranking')}, error: {str(e)}"
                                    )

                            product_dict = {
                                "sku":
                                sku_item,
                                "is_combo":
                                False,
                                "_ranking":
                                ranking_value,  # Internal use only, not sent to frontend
                                "name":
                                product_info.get("Product Name", "")
                                if product_info.get("Product Name") is not None
                                else "",
                                "image_url":
                                image_handler.generate_image_url(product_info),
                                "nominal_dimensions":
                                product_info.get("Nominal Dimensions", "")
                                if product_info.get("Nominal Dimensions")
                                is not None else "",
                                "brand":
                                product_info.get("Brand", "") if
                                product_info.get("Brand") is not None else "",
                                "series":
                                product_info.get("Series", "") if
                                product_info.get("Series") is not None else "",
                                "glass_thickness":
                                product_info.get("Glass Thickness", "")
                                if product_info.get("Glass Thickness")
                                is not None else "",
                                "door_type":
                                get_fixed_door_type(product_info),
                                "max_door_width":
                                product_info.get("Maximum Width", "")
                                if product_info.get("Maximum Width")
                                is not None else "",
                                "material":
                                product_info.get("Material", "")
                                if product_info.get("Material") is not None
                                else "",
                                "product_page_url":
                                product_info.get("Product Page URL", "")
                                if product_info.get("Product Page URL")
                                is not None else ""
                            }
                            enhanced_skus.append(product_dict)

                # Sort products by ranking value (lowest ranking first)
                enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                logger.debug(
                    f"Sorted {len(enhanced_skus)} products by ranking for category {category}"
                )

                compatible_products.append({
                    "category": category,
                    "products": enhanced_skus
                })
            
            logger.info(f"After shower base processing, incompatibility_reasons: {incompatibility_reasons}")

        # BACKWARDS COMPATIBILITY: Find bases/bathtubs compatible with doors
        elif product_category in ['Shower Doors', 'Tub Doors']:
            logger.debug(
                f"Using backward compatibility logic for door SKU: {sku}")

            # Get key door properties
            door_min_width = product_info.get("Minimum Width")
            door_max_width = product_info.get("Maximum Width")
            door_max_height = product_info.get("Maximum Height")
            door_series = product_info.get("Series")
            door_brand = product_info.get("Brand")
            door_has_return = product_info.get("Has Return Panel") == "Yes"
            door_family = product_info.get("Family")
            door_type = product_info.get("Type", "").lower()

            logger.debug(
                f"Door properties: Min Width={door_min_width}, Max Width={door_max_width}, Max Height={door_max_height}, Series={door_series}"
            )
            logger.debug(
                f"Door has return: {door_has_return}, Family: {door_family}, Type: {door_type}"
            )

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
                    if (tub_install == "Alcove" and pd.notna(tub_width)
                            and pd.notna(door_min_width)
                            and pd.notna(door_max_width)
                            and door_min_width <= tub_width <= door_max_width
                            and bathtub_compatibility.series_compatible(
                                tub_series, door_series)):

                        # Format tub data for the frontend
                        tub_data = tub.to_dict()
                        # Remove any NaN values
                        tub_data = {
                            k: v
                            for k, v in tub_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            tub_id,
                            "is_combo":
                            False,
                            "_ranking":
                            tub_data.get("Ranking", 999),
                            "name":
                            tub_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(tub_data),
                            "nominal_dimensions":
                            tub_data.get("Nominal Dimensions", ""),
                            "brand":
                            tub_data.get("Brand", ""),
                            "series":
                            tub_data.get("Series", ""),
                            "max_door_width":
                            tub_data.get("Max Door Width", ""),
                            "installation":
                            tub_data.get("Installation", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
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
                    base_brand = base.get("Brand")
                    base_fit_return = base.get("Fits Return Panel Size")
                    base_id = str(base.get("Unique ID", "")).strip()

                    # Match criteria for alcove installation
                    alcove_match = (
                        "alcove" in base_install and pd.notna(base_width)
                        and pd.notna(door_min_width)
                        and pd.notna(door_max_width)
                        and door_min_width <= base_width <= door_max_width
                        and base_compatibility.series_compatible(
                            base_series, door_series, base_brand, door_brand))

                    # Match criteria for corner installation with return panel
                    corner_match = (
                        "corner" in base_install and door_has_return
                        and pd.notna(base_width) and pd.notna(door_min_width)
                        and pd.notna(door_max_width)
                        and door_min_width <= base_width <= door_max_width
                        and base_compatibility.series_compatible(
                            base_series, door_series, base_brand, door_brand))

                    if alcove_match or corner_match:
                        # Format base data for the frontend
                        base_data = base.to_dict()
                        # Remove any NaN values
                        base_data = {
                            k: v
                            for k, v in base_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            base_id,
                            "is_combo":
                            False,
                            "_ranking":
                            base_data.get("Ranking", 999),
                            "name":
                            base_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(base_data),
                            "nominal_dimensions":
                            base_data.get("Nominal Dimensions", ""),
                            "brand":
                            base_data.get("Brand", ""),
                            "series":
                            base_data.get("Series", ""),
                            "max_door_width":
                            base_data.get("Max Door Width", ""),
                            "installation":
                            base_data.get("Installation", ""),
                            "material":
                            base_data.get("Material", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
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
                    if (shower_install == "Alcove" and pd.notna(shower_width)
                            and pd.notna(shower_height)
                            and pd.notna(door_min_width)
                            and pd.notna(door_max_width)
                            and pd.notna(door_max_height) and
                            door_min_width <= shower_width <= door_max_width
                            and door_max_height <= shower_height
                            and shower_compatibility.series_compatible(
                                shower_series, door_series)):
                        # Format shower data for the frontend
                        shower_data = shower.to_dict()
                        # Remove any NaN values
                        shower_data = {
                            k: v
                            for k, v in shower_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            shower_id,
                            "is_combo":
                            False,
                            "_ranking":
                            shower_data.get("Ranking", 999),
                            "name":
                            shower_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(shower_data),
                            "nominal_dimensions":
                            shower_data.get("Nominal Dimensions", ""),
                            "brand":
                            shower_data.get("Brand", ""),
                            "series":
                            shower_data.get("Series", ""),
                            "max_door_width":
                            shower_data.get("Max Door Width", ""),
                            "max_door_height":
                            shower_data.get("Max Door Height", ""),
                            "installation":
                            shower_data.get("Installation", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
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
                    if (pd.notna(tubshower_width)
                            and pd.notna(tubshower_height)
                            and pd.notna(door_min_width)
                            and pd.notna(door_max_width)
                            and pd.notna(door_max_height) and
                            door_min_width <= tubshower_width <= door_max_width
                            and door_max_height <= tubshower_height
                            and tubshower_compatibility.series_compatible(
                                tubshower_series, door_series)):
                        # Format tub shower data for the frontend
                        tubshower_data = tubshower.to_dict()
                        # Remove any NaN values
                        tubshower_data = {
                            k: v
                            for k, v in tubshower_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            tubshower_id,
                            "is_combo":
                            False,
                            "_ranking":
                            tubshower_data.get("Ranking", 999),
                            "name":
                            tubshower_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(tubshower_data),
                            "nominal_dimensions":
                            tubshower_data.get("Nominal Dimensions", ""),
                            "brand":
                            tubshower_data.get("Brand", ""),
                            "series":
                            tubshower_data.get("Series", ""),
                            "max_door_width":
                            tubshower_data.get("Max Door Width", ""),
                            "max_door_height":
                            tubshower_data.get("Max Door Height", ""),
                            "material":
                            tubshower_data.get("Material", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
                        }
                        tubshower_matches.append(product_dict)

                # Sort tub showers by ranking
                if tubshower_matches:
                    tubshower_matches.sort(
                        key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Tub Showers",
                        "products": tubshower_matches
                    })

        # BACKWARDS COMPATIBILITY: Find bases/bathtubs compatible with walls
        elif product_category == 'Walls':
            logger.debug(
                f"Using backward compatibility logic for wall SKU: {sku}")

            # Get key wall properties
            wall_type = str(product_info.get("Type", "")).lower()
            wall_brand = product_info.get("Brand")
            wall_family = product_info.get("Family")
            wall_series = product_info.get("Series")
            wall_nominal = product_info.get("Nominal Dimensions")
            wall_length = product_info.get("Length")
            wall_width = product_info.get("Width")
            wall_cut = product_info.get("Cut to Size")

            logger.debug(
                f"Wall properties: Type={wall_type}, Brand={wall_brand}, Family={wall_family}, Series={wall_series}"
            )
            logger.debug(
                f"Wall dimensions: Nominal={wall_nominal}, Length={wall_length}, Width={wall_width}, Cut to Size={wall_cut}"
            )

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
                        tub_brand, tub_family, wall_brand, wall_family)

                    # Check series compatibility
                    series_match = bathtub_compatibility.series_compatible(
                        tub_series, wall_series)

                    # Skip if no brand or series match
                    if not (brand_match and series_match):
                        continue

                    # Match criteria - exact nominal dimensions
                    nominal_match = False
                    if wall_cut != "Yes" and tub_nominal == wall_nominal:
                        nominal_match = True

                    # Match criteria - cut to size walls
                    cut_match = False
                    if (wall_cut == "Yes" and pd.notna(tub_length)
                            and pd.notna(tub_width) and pd.notna(wall_length)
                            and pd.notna(wall_width)
                            and wall_length >= tub_length
                            and wall_width >= tub_width):
                        cut_match = True

                    if nominal_match or cut_match:
                        # Format tub data for the frontend
                        tub_data = tub.to_dict()
                        # Remove any NaN values
                        tub_data = {
                            k: v
                            for k, v in tub_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            tub_id,
                            "is_combo":
                            False,
                            "_ranking":
                            tub_data.get("Ranking", 999),
                            "name":
                            tub_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(tub_data),
                            "nominal_dimensions":
                            tub_data.get("Nominal Dimensions", ""),
                            "brand":
                            tub_data.get("Brand", ""),
                            "series":
                            tub_data.get("Series", ""),
                            "max_door_width":
                            tub_data.get("Max Door Width", ""),
                            "installation":
                            tub_data.get("Installation", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
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
                        base_brand, base_family, wall_brand, wall_family)

                    # Check series compatibility
                    series_match = base_compatibility.series_compatible(
                        base_series, wall_series, base_brand, wall_brand)

                    # Skip if no brand or series match
                    if not (brand_match and series_match):
                        continue

                    # Match criteria - exact nominal dimensions
                    nominal_match = False
                    if wall_cut != "Yes" and base_nominal == wall_nominal:
                        nominal_match = True

                    # Match criteria - cut to size walls
                    cut_match = False
                    if (wall_cut == "Yes" and pd.notna(base_length)
                            and pd.notna(base_width_actual)
                            and pd.notna(wall_length) and pd.notna(wall_width)
                            and wall_length >= base_length
                            and wall_width >= base_width_actual):
                        cut_match = True

                    if nominal_match or cut_match:
                        # Format base data for the frontend
                        base_data = base.to_dict()
                        # Remove any NaN values
                        base_data = {
                            k: v
                            for k, v in base_data.items() if pd.notna(v)
                        }

                        product_dict = {
                            "sku":
                            base_id,
                            "is_combo":
                            False,
                            "_ranking":
                            base_data.get("Ranking", 999),
                            "name":
                            base_data.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(base_data),
                            "nominal_dimensions":
                            base_data.get("Nominal Dimensions", ""),
                            "brand":
                            base_data.get("Brand", ""),
                            "series":
                            base_data.get("Series", ""),
                            "max_door_width":
                            base_data.get("Max Door Width", ""),
                            "installation":
                            base_data.get("Installation", ""),
                            "material":
                            base_data.get("Material", ""),
                            "product_page_url":
                            product_info.get("Product Page URL", "")
                            if isinstance(product_info, dict) else
                            "" if "product_info" in locals() else base_data.
                            get("Product Page URL", "") if "base_data" in
                            locals() else tub_data.get("Product Page URL", "")
                            if "tub_data" in locals() else shower_data.
                            get("Product Page URL", "") if "shower_data" in
                            locals() else wall_info.
                            get("Product Page URL", "") if "wall_info" in
                            locals() else tubshower_data.
                            get("Product Page URL", "") if "tubshower_data" in
                            locals() else ""
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
            if 'Compatible Doors' in product_info and product_info.get(
                    'Compatible Doors') and pd.notna(
                        product_info['Compatible Doors']):
                doors_value = str(product_info['Compatible Doors'])
                if '|' in doors_value:
                    # Pipe-delimited values
                    compatible_doors = doors_value.split('|')
                else:
                    # Comma-delimited values
                    compatible_doors = doors_value.split(',')

                enhanced_skus = []
                for door_sku in [
                        door.strip() for door in compatible_doors
                        if door.strip()
                ]:
                    door_info = get_product_details(data, door_sku)
                    if door_info:
                        # Get ranking value for explicitly listed compatible product
                        ranking_value = 999  # Default high ranking if not specified
                        if "Ranking" in door_info and door_info[
                                "Ranking"] is not None:
                            try:
                                # Make sure we're converting to float properly
                                ranking_str = str(door_info["Ranking"]).strip()
                                if ranking_str:
                                    ranking_value = float(ranking_str)
                                    logger.debug(
                                        f"Using ranking {ranking_value} for door {door_sku}"
                                    )
                            except (ValueError, TypeError) as e:
                                logger.debug(
                                    f"Invalid ranking value for {door_sku}: {door_info.get('Ranking')}, error: {str(e)}"
                                )

                        enhanced_skus.append({
                            "sku":
                            door_sku,
                            "is_combo":
                            False,
                            "_ranking":
                            ranking_value,  # Internal use only, not sent to frontend
                            "name":
                            door_info.get("Product Name", "") if
                            door_info.get("Product Name") is not None else "",
                            "image_url":
                            image_handler.generate_image_url(door_info),
                            "nominal_dimensions":
                            door_info.get("Nominal Dimensions", "")
                            if door_info.get("Nominal Dimensions") is not None
                            else "",
                            "brand":
                            door_info.get("Brand", "")
                            if door_info.get("Brand") is not None else "",
                            "series":
                            door_info.get("Series", "")
                            if door_info.get("Series") is not None else "",
                            "glass_thickness":
                            door_info.get("Glass Thickness", "")
                            if door_info.get("Glass Thickness") is not None
                            else "",
                            "door_type":
                            get_fixed_door_type(door_info),
                            "max_door_width":
                            door_info.get("Maximum Width", "") if
                            door_info.get("Maximum Width") is not None else ""
                        })

                if enhanced_skus:
                    # Sort products by ranking value (lowest ranking first)
                    enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                    logger.debug(
                        f"Sorted {len(enhanced_skus)} products by ranking for Doors category"
                    )

                    compatible_products.append({
                        "category": "Doors",
                        "products": enhanced_skus
                    })

            # Check for explicitly listed compatible walls
            if 'Compatible Walls' in product_info and product_info.get(
                    'Compatible Walls') and pd.notna(
                        product_info['Compatible Walls']):
                walls_value = str(product_info['Compatible Walls'])
                if '|' in walls_value:
                    # Pipe-delimited values
                    compatible_walls = walls_value.split('|')
                else:
                    # Comma-delimited values
                    compatible_walls = walls_value.split(',')

                enhanced_skus = []
                for wall_sku in [
                        wall.strip() for wall in compatible_walls
                        if wall.strip()
                ]:
                    wall_info = get_product_details(data, wall_sku)
                    if wall_info:
                        # Get ranking value for walls
                        ranking_value = 999  # Default high ranking if not specified
                        if "Ranking" in wall_info and wall_info[
                                "Ranking"] is not None:
                            try:
                                # Make sure we're converting to float properly
                                ranking_str = str(wall_info["Ranking"]).strip()
                                if ranking_str:
                                    ranking_value = float(ranking_str)
                                    logger.debug(
                                        f"Using ranking {ranking_value} for wall {wall_sku}"
                                    )
                            except (ValueError, TypeError) as e:
                                logger.debug(
                                    f"Invalid ranking value for wall {wall_sku}: {wall_info.get('Ranking')}, error: {str(e)}"
                                )

                        enhanced_skus.append({
                            "sku":
                            wall_sku,
                            "is_combo":
                            False,
                            "_ranking":
                            ranking_value,  # Internal use only, not sent to frontend
                            "name":
                            wall_info.get("Product Name", ""),
                            "image_url":
                            image_handler.generate_image_url(wall_info),
                            "nominal_dimensions":
                            wall_info.get("Nominal Dimensions", ""),
                            "brand":
                            wall_info.get("Brand", ""),
                            "series":
                            wall_info.get("Series", ""),
                            "product_page_url":
                            wall_info.get("Product Page URL", "")
                        })

                if enhanced_skus:
                    # Sort products by ranking value (lowest ranking first)
                    enhanced_skus.sort(key=lambda x: x.get('_ranking', 999))
                    logger.debug(
                        f"Sorted {len(enhanced_skus)} products by ranking for Walls category"
                    )

                    compatible_products.append({
                        "category": "Walls",
                        "products": enhanced_skus
                    })

        # ENCLOSURES: Find compatible shower bases for enclosures (reverse of base→enclosure logic)
        elif product_category == 'Enclosures':
            logger.debug(f"Using enclosure reverse compatibility logic for SKU: {sku}")
            
            # Get enclosure properties (these become the constraints)
            enc_nominal = product_info.get("Nominal Dimensions", "")
            enc_door_width = product_info.get("Door Width")
            enc_return_width = product_info.get("Return Panel Width")
            enc_brand = product_info.get("Brand")
            enc_series = product_info.get("Series")
            
            logger.info(f"Enclosure: {enc_nominal}, Door: {enc_door_width}, Return: {enc_return_width}")
            logger.info(f"Enclosure Brand: {enc_brand}, Series: {enc_series}")
            
            # Parse enclosure dimensions
            try:
                if enc_nominal and 'x' in str(enc_nominal):
                    dimensions = str(enc_nominal).split('x')
                    enc_length = float(dimensions[0].strip())
                    enc_width_actual = float(dimensions[1].strip())
                else:
                    enc_length = None
                    enc_width_actual = None
            except (ValueError, IndexError):
                enc_length = None
                enc_width_actual = None
            
            # Find compatible shower bases (mirror the existing logic from base_compatibility.py)
            if 'Shower Bases' in data:
                matching_bases = []
                bases_df = data['Shower Bases']
                tolerance = 3.0
                
                for _, base in bases_df.iterrows():
                    base_install = str(base.get("Installation", "")).lower()
                    base_id = str(base.get("Unique ID", "")).strip()
                    
                    # Only check corner bases (enclosures require corner installation)
                    if "corner" not in base_install or not base_id:
                        continue
                        
                    base_series = base.get("Series")
                    base_brand = base.get("Brand")
                    base_nominal = base.get("Nominal Dimensions")
                    base_length = base.get("Length")
                    base_width_actual = base.get("Width Actual")
                    
                    logger.debug(f"  Checking base: {base_id}")
                    
                    # Check series compatibility (same as original)
                    series_match = base_compatibility.series_compatible(enc_series, base_series, enc_brand, base_brand)
                    if not series_match:
                        logger.debug(f"    ✗ Series mismatch")
                        continue
                    
                    # Check nominal dimensions match
                    nominal_match = base_nominal == enc_nominal
                    
                    # Check detailed dimension compatibility (reversed from original logic)
                    dimension_match = False
                    if (pd.notna(enc_length) and pd.notna(base_length) and 
                        pd.notna(enc_width_actual) and pd.notna(base_width_actual) and
                        pd.notna(enc_door_width) and pd.notna(enc_return_width)):
                        try:
                            dimension_match = (
                                float(base_length) >= float(enc_door_width) and
                                (float(base_length) - float(enc_door_width)) <= tolerance and
                                float(base_width_actual) >= float(enc_return_width) and
                                (float(base_width_actual) - float(enc_return_width)) <= tolerance
                            )
                        except (ValueError, TypeError):
                            dimension_match = False
                    
                    logger.debug(f"    Nominal: {nominal_match}, Dimension: {dimension_match}")
                    
                    # Accept if either match (same as original logic)
                    if nominal_match or dimension_match:
                        base_product = {
                            "sku": base_id,
                            "name": base.get("Product Name", ""),
                            "brand": base.get("Brand", ""),
                            "series": base.get("Series", ""),
                            "category": "Shower Bases",
                            "image_url": base.get("Image URL", ""),
                            "product_page_url": base.get("Product Page URL", ""),
                            "_ranking": base.get("Ranking", 999),
                            "is_combo": False
                        }
                        matching_bases.append(base_product)
                        logger.debug(f"    ✓ Added base {base_id}")
                
                # Add results if any matches found
                if matching_bases:
                    sorted_bases = sorted(matching_bases, key=lambda x: x.get('_ranking', 999))
                    compatible_products.append({
                        "category": "Shower Bases",
                        "products": sorted_bases
                    })
                    logger.debug(f"Added {len(sorted_bases)} shower bases")

        # THIS IS THE ROOT CAUSE FIX: Always get the correct original product information
        # before proceeding with compatibility checks

        # Before finding compatibles, preserve the original source product information
        # so it doesn't get overwritten during the compatibility search process
        logger.debug(
            f"Creating source product details for SKU: {sku} in category: {product_category}"
        )

        # Make a separate request to get the accurate source product info
        # This ensures we always use the right product information
        original_product_info = None

        # Search all worksheets for the exact SKU to get the correct product information
        # This is a comprehensive solution to ensure we get the right product details
        # regardless of which worksheet it comes from
        for sheet_name, df in data.items():
            if 'Unique ID' in df.columns:
                # Case-insensitive search for the SKU
                matching_rows = df[df['Unique ID'].astype(str).str.upper() ==
                                   sku.upper()]
                if not matching_rows.empty:
                    original_product_info = matching_rows.iloc[0].to_dict()
                    logger.debug(
                        f"Found original product in {sheet_name}: {original_product_info.get('Product Name', 'Unknown')}"
                    )
                    # Update the category if it's different
                    product_category = sheet_name
                    break  # Stop once we find a direct match

        # If we couldn't find the original product in any category, use what we have
        if original_product_info is None:
            original_product_info = product_info if product_info is not None else {}
            logger.debug(
                f"Using found product info: {original_product_info.get('Product Name', 'Unknown')}"
            )

        # Create a source product with the correct information
        source_product = {
            "sku":
            sku,
            "category":
            product_category,
            "name":
            original_product_info.get("Product Name", "")
            if original_product_info.get("Product Name") is not None else "",
            "image_url":
            image_handler.generate_image_url(original_product_info),
            "nominal_dimensions":
            original_product_info.get("Nominal Dimensions", "")
            if original_product_info.get("Nominal Dimensions") is not None else
            "",
            "installation":
            original_product_info.get("Installation", "")
            if original_product_info.get("Installation") is not None else "",
            "brand":
            original_product_info.get("Brand", "")
            if original_product_info.get("Brand") is not None else "",
            "series":
            original_product_info.get("Series", "")
            if original_product_info.get("Series") is not None else "",
            "family":
            original_product_info.get("Family", "")
            if original_product_info.get("Family") is not None else "",
            "product_page_url":
            original_product_info.get("Product Page URL", "") if
            original_product_info.get("Product Page URL") is not None else "",
        }

        # Handle max_door_width - this field has different column names in different sheets
        # For Shower Bases, Bathtubs, Showers, and Tub Showers, use "Max Door Width", for doors use "Maximum Width"
        if product_category in [
                "Bathtubs", "Shower Bases", "Showers", "Tub Showers"
        ]:
            source_product["max_door_width"] = original_product_info.get(
                "Max Door Width", "") if original_product_info.get(
                    "Max Door Width") is not None else ""
            logger.debug(
                f"Using Max Door Width from {product_category}: {source_product['max_door_width']}"
            )
        else:
            source_product["max_door_width"] = original_product_info.get(
                "Maximum Width", "") if original_product_info.get(
                    "Maximum Width") is not None else ""
            logger.debug(
                f"Using Maximum Width from {product_category}: {source_product['max_door_width']}"
            )

        # Handle max_door_height for Showers and Tub Showers
        if product_category in ["Showers", "Tub Showers"]:
            source_product["max_door_height"] = original_product_info.get(
                "Max Door Height", "") if original_product_info.get(
                    "Max Door Height") is not None else ""
            logger.debug(
                f"Using Max Door Height from {product_category}: {source_product.get('max_door_height', 'N/A')}"
            )

        logger.debug(f"Source product name (final): {source_product['name']}")

        # Early return for shower bases with incompatibility reasons only
        if product_category == 'Shower Bases' and incompatibility_reasons and not compatible_products:
            logger.info(f"Early return for shower base with incompatibility reasons: {incompatibility_reasons}")
            return {"product": source_product, "compatibles": [], "incompatibility_reasons": incompatibility_reasons}

        # Ensure every category dict has a "products" key (only for categories without incompatibility reasons)
        for cat in compatible_products:
            if "reason" not in cat:
                cat.setdefault("products", [])

        # Process whitelist overrides for products with incompatibility reasons
        # (Bathtubs, Shower Bases, Showers, Tub Showers)
        if product_category in ['Bathtubs', 'Shower Bases', 'Showers', 'Tub Showers']:
            logger.debug(f"Processing whitelist overrides for {product_category} SKU: {sku}")
            
            # Process whitelist to potentially override incompatibility reasons
            whitelist_skus = whitelist_helper.get_whitelist_for_sku(sku)
            whitelist_overrides = {}  # category -> list of whitelisted products
            
            for wl_sku in whitelist_skus:
                # Find the whitelisted product in the data
                wl_category = None
                wl_row = None
                
                for category_name, df in data.items():
                    product_row = df[df['Unique ID'].astype(str).str.strip() == wl_sku]
                    if not product_row.empty:
                        wl_category = category_name
                        wl_row = product_row.iloc[0]
                        break
                
                if wl_row is not None and wl_category:
                    # Create the whitelisted product
                    def _clean(v):
                        if pd.isna(v):
                            return ""
                        return str(v).strip()
                    
                    # Convert None values back to empty strings for image URL generation
                    # The image handler expects pandas-style data, not None values
                    wl_row_fixed = {}
                    for key, value in wl_row.items():
                        if value is None:
                            wl_row_fixed[key] = ""
                        else:
                            wl_row_fixed[key] = value
                    
                    # Generate image URL with the corrected data format
                    image_url = image_handler.generate_image_url(wl_row_fixed)
                    
                    wl_product = {
                        "sku": wl_sku,
                        "name": _clean(wl_row.get("Product Name", "")),
                        "brand": _clean(wl_row.get("Brand", "")),
                        "series": _clean(wl_row.get("Series", "")),
                        "category": wl_category,
                        "glass_thickness": _clean(wl_row.get("Glass Thickness", "")),
                        "door_type": _clean(wl_row.get("Door Type", "")),
                        "image_url": image_url,
                        "product_page_url": _clean(wl_row.get("Product Page URL", "")),
                        "is_combo": False
                    }
                    
                    if wl_category not in whitelist_overrides:
                        whitelist_overrides[wl_category] = []
                    whitelist_overrides[wl_category].append(wl_product)
                    logger.info(f"Whitelist override for {product_category} {sku}: Added {wl_sku} to {wl_category}")
            
            # Process compatibility results with whitelist overrides
            final_compatibles = []
            
            for category in compatible_products:
                if "reason" in category:
                    # Check if this incompatibility reason category has whitelist overrides
                    category_name = category["category"]
                    if category_name in whitelist_overrides:
                        # Replace incompatibility reason with whitelisted products
                        final_compatibles.append({
                            "category": category_name,
                            "products": whitelist_overrides[category_name]
                        })
                        logger.info(f"Whitelist override: Replaced incompatibility reason for {category_name} with {len(whitelist_overrides[category_name])} whitelisted products")
                    else:
                        # Keep the incompatibility reason
                        final_compatibles.append(category)
                elif "products" in category and category["products"]:
                    # Regular category with products - add any whitelist overrides and remove _ranking fields
                    category_name = category["category"]
                    all_products = list(category["products"])
                    
                    # Add whitelisted products if any
                    if category_name in whitelist_overrides:
                        all_products.extend(whitelist_overrides[category_name])
                        logger.info(f"Whitelist addition: Added {len(whitelist_overrides[category_name])} whitelisted products to {category_name}")

                    # Remove _ranking fields
                    for product in all_products:
                        if "_ranking" in product:
                            del product["_ranking"]
                    
                    final_compatibles.append({
                        "category": category_name,
                        "products": all_products
                    })
            
            # Add any whitelist categories that weren't in the original results
            for wl_category, wl_products in whitelist_overrides.items():
                if not any(cat["category"] == wl_category for cat in final_compatibles):
                    final_compatibles.append({
                        "category": wl_category,
                        "products": wl_products
                    })
                    logger.info(f"Whitelist addition: Added new category {wl_category} with {len(wl_products)} whitelisted products")
            
            return {
                "product": source_product,
                "compatibles": final_compatibles
            }

        # === BLACKLIST helper and filter ===
        def _extract_sku(prod):
            if not isinstance(prod, dict):
                return str(prod).strip()
            for k in ("sku", "SKU", "Unique ID", "unique_id"):
                if k in prod and prod[k]:
                    return str(prod[k]).strip()
            if prod.get("is_combo"):
                main = str(prod.get("main_product", {}).get("sku", "")).strip()
                sec = str(prod.get("secondary_product", {}).get("sku",
                                                                "")).strip()
                return f"{main}|{sec}".strip("|")
            return ""

        for cat in compatible_products:
            # Only process categories that have products (not incompatibility reasons)
            if "products" in cat:
                before = len(cat["products"])
                cat["products"] = [
                    p for p in cat["products"]
                    if not blacklist_helper.is_blacklisted(sku, _extract_sku(p))
                ]
                if before != len(cat["products"]):
                    logger.info("Blacklist removed %d item(s) from %s for SKU %s",
                                before - len(cat["products"]),
                                cat.get("category", ""), sku)
        # Keep categories that have products OR incompatibility reasons
        compatible_products = [c for c in compatible_products if c.get("products") or c.get("reason")]
        
        for wl_sku in whitelist_helper.get_whitelist_for_sku(sku):
            # Skip if already present (only check categories that have products)
            if any(_extract_sku(p) == wl_sku
                   for c in compatible_products 
                   if "products" in c
                   for p in c["products"]):
                continue

            # Locate row & category
            wl_row = get_product_details(data, wl_sku)
            if wl_row is None:
                continue
            wl_category = next(
                (name for name, df in data.items()
                 if "Unique ID" in df.columns
                 and not df[df["Unique ID"].astype(str)
                               .str.upper()
                               .eq(wl_sku.upper())].empty),
                None,
            )
            if wl_category is None:
                continue

            # Clean NaN values
            def _clean(v):
                return "" if (v is None or (isinstance(v, float) and np.isnan(v))) else v

            # Build the same structure the rule engines create
            wl_product = {
                "sku": wl_sku,
                "name":     _clean(wl_row.get("Product Name", "")),
                "brand":    _clean(wl_row.get("Brand", "")),
                "series":   _clean(wl_row.get("Series", "")),
                "category": wl_category,
                "glass_thickness": _clean(wl_row.get("Glass Thickness", "")),
                "door_type":       _clean(wl_row.get("Door Type", "")),
                "image_url": image_handler.generate_image_url(wl_row),
                "_ranking":     _clean(wl_row.get("Ranking", ""))
            }

            # Attach to existing category or create a new one
            target = next((c for c in compatible_products
                           if c["category"] == wl_category), None)
            if target is None:
                target = {"category": wl_category, "products": []}
                compatible_products.append(target)
            elif "products" not in target:
                # This category has an incompatibility reason, add products field
                target["products"] = []
            target["products"].append(wl_product)
        # === END BLACKLIST helper and filter ===

        # For all other product types, process as usual
        # Sort each category's products by ranking (lowest to highest)
        # And remove the internal _ranking field before sending to frontend
        for category in compatible_products:
            if "products" in category and category["products"]:
                # First log the products before sorting (for debugging)
                logger.debug(
                    f"Products in {category['category']} before sorting:")
                for idx, product in enumerate(category["products"]):
                    if product.get("is_combo", False):
                        sku_display = f"{product['main_product']['sku']}|{product['secondary_product']['sku']}"
                    else:
                        sku_display = product.get('sku', 'Unknown')

                    ranking = product.get("_ranking", 999)
                    name = product.get('name', '')
                    if not name and product.get("is_combo", False):
                        name = product.get('main_product', {}).get('name', '')

                    logger.debug(
                        f"  {idx}: {sku_display} ({name}) - Ranking: {ranking}"
                    )

                # Sort products based on the _ranking field (ascending order)
                # First ensure all ranking values are properly converted to float
                for product in category["products"]:
                    if "_ranking" in product:
                        try:
                            original_val = product["_ranking"]
                            product["_ranking"] = float(product["_ranking"])
                            # Log if conversion changes the value
                            if original_val != product["_ranking"]:
                                logger.debug(
                                    f"Converted ranking from {original_val} to {product['_ranking']}"
                                )
                        except (ValueError, TypeError) as e:
                            logger.debug(
                                f"Invalid ranking value: {product['_ranking']}, error: {str(e)}"
                            )
                            product["_ranking"] = 999

                # Now sort with proper numeric comparison
                category["products"].sort(key=lambda p: p.get("_ranking", 999))

                # Log the products after sorting (for debugging)
                logger.debug(
                    f"Products in {category['category']} after sorting:")
                for idx, product in enumerate(category["products"]):
                    if product.get("is_combo", False):
                        sku_display = f"{product['main_product']['sku']}|{product['secondary_product']['sku']}"
                    else:
                        sku_display = product.get('sku', 'Unknown')

                    ranking = product.get("_ranking", 999)
                    name = product.get('name', '')
                    if not name and product.get("is_combo", False):
                        name = product.get('main_product', {}).get('name', '')

                    logger.debug(
                        f"  {idx}: {sku_display} ({name}) - Ranking: {ranking}"
                    )

                # Remove the _ranking field from each product as it's for internal use only
                for product in category["products"]:
                    if "_ranking" in product:
                        del product["_ranking"]

        logger.info(f"Before final return - incompatibility_reasons still has: {incompatibility_reasons}")
        logger.debug(f"Found {len(compatible_products)} compatible categories")
        logger.info(f"About to return - incompatibility_reasons: {incompatibility_reasons}")
        logger.info(f"About to return - len(incompatibility_reasons): {len(incompatibility_reasons)}")
        
        result = {"product": source_product, "compatibles": compatible_products, "incompatibility_reasons": incompatibility_reasons}
        logger.info(f"Final result incompatibility_reasons: {result.get('incompatibility_reasons', {})}")
        return result

    except Exception as e:
        import traceback
        logger.error(f"Error in find_compatible_products: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"product": None, "compatibles": [], "incompatibility_reasons": {}}


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
            product_row = df[df['Unique ID'].astype(str).str.upper() ==
                             sku.upper()]

            if not product_row.empty:
                # Convert to dict and clean up NaN values
                product_info = product_row.iloc[0].to_dict()

                # Clean up NaN values in the dictionary
                for key, value in product_info.items():
                    if pd.isna(value):
                        product_info[key] = None

                # Add the category to the product info
                product_info['_source_category'] = category

                logger.debug(
                    f"Found product in {category}: {product_info.get('Product Name', 'Unknown')}"
                )
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
