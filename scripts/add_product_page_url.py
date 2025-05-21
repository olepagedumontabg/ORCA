"""
Script to update compatibility.py to include the product_page_url field in all product dictionaries
"""

import re
import os

def add_product_page_url_to_product_dicts():
    """Add product_page_url field to all product dictionaries in compatibility.py"""
    
    compatibility_path = 'logic/compatibility.py'
    
    # Read the file
    with open(compatibility_path, 'r') as file:
        content = file.read()
    
    # Regular expression to find product dictionary patterns
    pattern = r'product_dict\s*=\s*\{[^}]*?\}'
    
    # Function to replace each match
    def replacement(match):
        # If product_page_url is already in the pattern, don't modify it
        if 'product_page_url' in match.group(0):
            return match.group(0)
        
        # Otherwise, add the product_page_url field before the closing brace
        return match.group(0).replace('}', ',\n                            "product_page_url": product_info.get("Product Page URL", "") if isinstance(product_info, dict) else ""' + 
                                     ' if "product_info" in locals() else base_data.get("Product Page URL", "") if "base_data" in locals() else' +
                                     ' tub_data.get("Product Page URL", "") if "tub_data" in locals() else' +
                                     ' shower_data.get("Product Page URL", "") if "shower_data" in locals() else' +
                                     ' wall_info.get("Product Page URL", "") if "wall_info" in locals() else' +
                                     ' tubshower_data.get("Product Page URL", "") if "tubshower_data" in locals() else ""' +
                                     '\n                        }')
    
    # Replace all matches
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the updated content back to the file
    with open(compatibility_path, 'w') as file:
        file.write(updated_content)
    
    print(f"Updated {compatibility_path} to include product_page_url in all product dictionaries")

if __name__ == '__main__':
    add_product_page_url_to_product_dicts()