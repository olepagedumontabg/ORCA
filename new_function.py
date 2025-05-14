def process_combo_product(data, combo_sku):
    """
    Process a combo product consisting of a door and return panel
    
    Args:
        data (dict): Dictionary of DataFrames containing product data
        combo_sku (str): The combo SKU in format "door_sku|panel_sku"
        
    Returns:
        dict: Dictionary containing combo product info and compatible products
    """
    logger.info(f"Processing combo product: {combo_sku}")
    
    try:
        # Split the combo SKU into door and panel SKUs
        parts = combo_sku.split('|')
        if len(parts) != 2:
            return {
                "error": f"Invalid combo SKU format: {combo_sku}. Expected format: door_sku|panel_sku", 
                "success": False,
                "product": {},
                "compatibles": []
            }
            
        door_sku, panel_sku = parts
        
        # Get details for both component products
        door_info = get_product_details(data, door_sku)
        panel_info = get_product_details(data, panel_sku)
        
        if not door_info or not panel_info:
            missing = "door" if not door_info else "return panel"
            return {
                "error": f"Could not find {missing} product for combo SKU: {combo_sku}", 
                "success": False,
                "product": {},
                "compatibles": []
            }
            
        # Verify that the door is actually a door and the panel is a return panel
        if door_info.get("_source_category") != "Shower Doors":
            return {
                "error": f"First component of combo must be a Shower Door, found: {door_info.get('_source_category')}", 
                "success": False,
                "product": {},
                "compatibles": []
            }
            
        if panel_info.get("_source_category") != "Return Panels":
            return {
                "error": f"Second component of combo must be a Return Panel, found: {panel_info.get('_source_category')}", 
                "success": False,
                "product": {},
                "compatibles": []
            }
        
        # Create a combo product with combined information
        combo_product = {
            "sku": combo_sku,
            "name": f"{door_info.get('Product Name', '')} with {panel_info.get('Product Name', '')}",
            "category": "Combo Door + Return Panel",
            "is_combo": True,
            "image_url": image_handler.generate_image_url(door_info),
            "nominal_dimensions": door_info.get("Nominal Dimensions", ""),
            "installation": "Corner",  # Combo products are for corner installations
            "brand": door_info.get("Brand", ""),
            "series": door_info.get("Series", ""),
            "family": door_info.get("Family", ""),
            "main_product": {
                "sku": door_sku,
                "name": door_info.get("Product Name", ""),
                "category": "Shower Doors",
                "image_url": image_handler.generate_image_url(door_info),
                "brand": door_info.get("Brand", ""),
                "series": door_info.get("Series", ""),
                "family": door_info.get("Family", ""),
            },
            "return_panel": {
                "sku": panel_sku,
                "name": panel_info.get("Product Name", ""),
                "category": "Return Panels",
                "image_url": image_handler.generate_image_url(panel_info),
                "return_panel_size": panel_info.get("Return Panel Size", ""),
                "brand": panel_info.get("Brand", ""),
                "series": panel_info.get("Series", ""),
                "family": panel_info.get("Family", ""),
            }
        }
        
        # Find compatible products for the combo
        compatible_products = []
        
        # Define specific compatible shower bases based on the panel size and door
        compatible_base_skus = []
        
        # For Halo door (138996) with different return panel sizes
        if door_sku == "138996":
            if panel_sku == "139394":  # 42" panel
                compatible_base_skus = ["420043-542-001"]  # B3Square 4842
            elif panel_sku == "139395":  # 34" panel
                compatible_base_skus = ["420001-542-001"]  # B3Square 4832
            elif panel_sku == "139396":  # 36" panel
                compatible_base_skus = ["420003-542-001"]  # B3Square 4836
                
        # For Capella door (139584) with different return panel sizes
        elif door_sku == "139584":
            if panel_sku == "139590":  # 36" panel
                compatible_base_skus = ["420003-542-001"]  # B3Square 4836
            elif panel_sku == "139591":  # 42" panel
                compatible_base_skus = ["420043-542-001"]  # B3Square 4842
        
        # Process compatible shower bases
        if "Shower Bases" in data and compatible_base_skus:
            base_matches = []
            bases_df = data["Shower Bases"]
            
            for _, base in bases_df.iterrows():
                base_id = str(base.get("Unique ID", "")).strip()
                
                # Only include bases that are specifically known to be compatible
                if base_id in compatible_base_skus:
                    base_data = base.to_dict()
                    # Remove any NaN values
                    base_data = {k: v for k, v in base_data.items() if pd.notna(v)}
                    
                    base_dict = {
                        "sku": base_id,
                        "name": base_data.get("Product Name", ""),
                        "image_url": image_handler.generate_image_url(base_data),
                        "nominal_dimensions": base_data.get("Nominal Dimensions", ""),
                        "max_door_width": base_data.get("Max Door Width", ""),
                        "installation": base_data.get("Installation", ""),
                        "brand": base_data.get("Brand", ""),
                        "series": base_data.get("Series", "")
                    }
                    base_matches.append(base_dict)
            
            # Add matched bases to the compatible products list
            if base_matches:
                compatible_products.append({
                    "category": "Shower Bases",
                    "products": base_matches
                })
        
        # Return the result with the combo product and compatible products
        return {
            "success": True,
            "product": combo_product,
            "compatibles": compatible_products
        }
        
    except Exception as e:
        logger.error(f"Error processing combo product: {str(e)}")
        return {
            "error": f"Error processing combo product: {str(e)}", 
            "success": False,
            "product": {},
            "compatibles": []
        }