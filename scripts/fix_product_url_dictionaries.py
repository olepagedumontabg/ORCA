"""
Script to manually update product dictionaries to include product_page_url field
"""

import re
import os

def fix_product_url_dictionaries():
    """Manually fix product dictionaries to include product_page_url field"""
    
    compatibility_path = 'logic/compatibility.py'
    
    # Read the file
    with open(compatibility_path, 'r') as file:
        content = file.read()
    
    # Define patterns for each type of product dictionary
    patterns = [
        # Pattern for bathtub dictionary in the bathtub_matches section
        (r'product_dict = \{\s*"sku": tub_id,\s*"is_combo": False,\s*"_ranking": tub_data\.get\("Ranking", 999\),\s*"name": tub_data\.get\("Product Name", ""\),\s*"image_url": image_handler\.generate_image_url\(tub_data\),\s*"nominal_dimensions": tub_data\.get\("Nominal Dimensions", ""\),\s*"brand": tub_data\.get\("Brand", ""\),\s*"series": tub_data\.get\("Series", ""\),\s*"max_door_width": tub_data\.get\("Max Door Width", ""\),\s*"installation": tub_data\.get\("Installation", ""\)\s*\}',
         r'product_dict = {\n                            "sku": tub_id,\n                            "is_combo": False,\n                            "_ranking": tub_data.get("Ranking", 999),\n                            "name": tub_data.get("Product Name", ""),\n                            "image_url": image_handler.generate_image_url(tub_data),\n                            "nominal_dimensions": tub_data.get("Nominal Dimensions", ""),\n                            "brand": tub_data.get("Brand", ""),\n                            "series": tub_data.get("Series", ""),\n                            "max_door_width": tub_data.get("Max Door Width", ""),\n                            "installation": tub_data.get("Installation", ""),\n                            "product_page_url": tub_data.get("Product Page URL", "")\n                        }'),
        
        # Pattern for base dictionary in the base_matches section
        (r'product_dict = \{\s*"sku": base_id,\s*"is_combo": False,\s*"_ranking": base_data\.get\("Ranking", 999\),\s*"name": base_data\.get\("Product Name", ""\),\s*"image_url": image_handler\.generate_image_url\(base_data\),\s*"nominal_dimensions": base_data\.get\("Nominal Dimensions", ""\),\s*"brand": base_data\.get\("Brand", ""\),\s*"series": base_data\.get\("Series", ""\),\s*"max_door_width": base_data\.get\("Max Door Width", ""\),\s*"installation": base_data\.get\("Installation", ""\)\s*\}',
         r'product_dict = {\n                            "sku": base_id,\n                            "is_combo": False,\n                            "_ranking": base_data.get("Ranking", 999),\n                            "name": base_data.get("Product Name", ""),\n                            "image_url": image_handler.generate_image_url(base_data),\n                            "nominal_dimensions": base_data.get("Nominal Dimensions", ""),\n                            "brand": base_data.get("Brand", ""),\n                            "series": base_data.get("Series", ""),\n                            "max_door_width": base_data.get("Max Door Width", ""),\n                            "installation": base_data.get("Installation", ""),\n                            "product_page_url": base_data.get("Product Page URL", "")\n                        }'),
        
        # Pattern for shower dictionary in the shower_matches section
        (r'product_dict = \{\s*"sku": shower_id,\s*"is_combo": False,\s*"_ranking": shower_data\.get\("Ranking", 999\),\s*"name": shower_data\.get\("Product Name", ""\),\s*"image_url": image_handler\.generate_image_url\(shower_data\),\s*"nominal_dimensions": shower_data\.get\("Nominal Dimensions", ""\),\s*"brand": shower_data\.get\("Brand", ""\),\s*"series": shower_data\.get\("Series", ""\),\s*"max_door_width": shower_data\.get\("Max Door Width", ""\),\s*"max_door_height": shower_data\.get\("Max Door Height", ""\),\s*"material": shower_data\.get\("Material", ""\)\s*\}',
         r'product_dict = {\n                            "sku": shower_id,\n                            "is_combo": False,\n                            "_ranking": shower_data.get("Ranking", 999),\n                            "name": shower_data.get("Product Name", ""),\n                            "image_url": image_handler.generate_image_url(shower_data),\n                            "nominal_dimensions": shower_data.get("Nominal Dimensions", ""),\n                            "brand": shower_data.get("Brand", ""),\n                            "series": shower_data.get("Series", ""),\n                            "max_door_width": shower_data.get("Max Door Width", ""),\n                            "max_door_height": shower_data.get("Max Door Height", ""),\n                            "material": shower_data.get("Material", ""),\n                            "product_page_url": shower_data.get("Product Page URL", "")\n                        }'),
        
        # Pattern for tubshower dictionary in the tubshower_matches section
        (r'product_dict = \{\s*"sku": tubshower_id,\s*"is_combo": False,\s*"_ranking": tubshower_data\.get\("Ranking", 999\),\s*"name": tubshower_data\.get\("Product Name", ""\),\s*"image_url": image_handler\.generate_image_url\(tubshower_data\),\s*"nominal_dimensions": tubshower_data\.get\("Nominal Dimensions", ""\),\s*"brand": tubshower_data\.get\("Brand", ""\),\s*"series": tubshower_data\.get\("Series", ""\),\s*"max_door_width": tubshower_data\.get\("Max Door Width", ""\),\s*"max_door_height": tubshower_data\.get\("Max Door Height", ""\),\s*"material": tubshower_data\.get\("Material", ""\)\s*\}',
         r'product_dict = {\n                            "sku": tubshower_id,\n                            "is_combo": False,\n                            "_ranking": tubshower_data.get("Ranking", 999),\n                            "name": tubshower_data.get("Product Name", ""),\n                            "image_url": image_handler.generate_image_url(tubshower_data),\n                            "nominal_dimensions": tubshower_data.get("Nominal Dimensions", ""),\n                            "brand": tubshower_data.get("Brand", ""),\n                            "series": tubshower_data.get("Series", ""),\n                            "max_door_width": tubshower_data.get("Max Door Width", ""),\n                            "max_door_height": tubshower_data.get("Max Door Height", ""),\n                            "material": tubshower_data.get("Material", ""),\n                            "product_page_url": tubshower_data.get("Product Page URL", "")\n                        }'),
        
        # Pattern for wall dictionaries
        (r'enhanced_skus\.append\(\{\s*"sku": wall_sku,\s*"is_combo": False,\s*"_ranking": ranking_value,\s*"name": wall_info\.get\("Product Name", ""\),\s*"image_url": image_handler\.generate_image_url\(wall_info\),\s*"nominal_dimensions": wall_info\.get\("Nominal Dimensions", ""\),\s*"brand": wall_info\.get\("Brand", ""\),\s*"series": wall_info\.get\("Series", ""\)\s*\}\)',
         r'enhanced_skus.append({\n                            "sku": wall_sku,\n                            "is_combo": False,\n                            "_ranking": ranking_value,\n                            "name": wall_info.get("Product Name", ""),\n                            "image_url": image_handler.generate_image_url(wall_info),\n                            "nominal_dimensions": wall_info.get("Nominal Dimensions", ""),\n                            "brand": wall_info.get("Brand", ""),\n                            "series": wall_info.get("Series", ""),\n                            "product_page_url": wall_info.get("Product Page URL", "")\n                        })'),
    ]
    
    # Apply each pattern replacement
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the updated content back to the file
    with open(compatibility_path, 'w') as file:
        file.write(content)
    
    # Now specifically fix the wall section by direct text replacement
    with open(compatibility_path, 'r') as file:
        content = file.read()
    
    # Specific replacement for wall dictionaries that might be missed by regex
    wall_pattern = """                        enhanced_skus.append({
                            "sku": wall_sku,
                            "is_combo": False,
                            "_ranking": ranking_value,  # Internal use only, not sent to frontend
                            "name": wall_info.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(wall_info),
                            "nominal_dimensions": wall_info.get("Nominal Dimensions", ""),
                            "brand": wall_info.get("Brand", ""),
                            "series": wall_info.get("Series", "")
                        })"""
    
    wall_replacement = """                        enhanced_skus.append({
                            "sku": wall_sku,
                            "is_combo": False,
                            "_ranking": ranking_value,  # Internal use only, not sent to frontend
                            "name": wall_info.get("Product Name", ""),
                            "image_url": image_handler.generate_image_url(wall_info),
                            "nominal_dimensions": wall_info.get("Nominal Dimensions", ""),
                            "brand": wall_info.get("Brand", ""),
                            "series": wall_info.get("Series", ""),
                            "product_page_url": wall_info.get("Product Page URL", "")
                        })"""
    
    content = content.replace(wall_pattern, wall_replacement)
    
    # Write the updated content back to the file
    with open(compatibility_path, 'w') as file:
        file.write(content)
    
    print(f"Updated {compatibility_path} to include product_page_url field in all product dictionaries")

if __name__ == '__main__':
    fix_product_url_dictionaries()