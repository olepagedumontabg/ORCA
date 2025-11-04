"""
Image URL handling functionality for the compatibility finder.
This module provides functions to generate and normalize image URLs for products.
"""

import logging
import re
import urllib.parse

# Configure logging
logger = logging.getLogger(__name__)

def generate_image_url(product_info):
    """
    Generate an image URL for a product based on available information.
    
    Args:
        product_info (dict): Product information dictionary
        
    Returns:
        str: Image URL or empty string if not available
    """
    # Check if product_info is valid
    if product_info is None or not isinstance(product_info, dict):
        return ""
        
    # First, check if we have an explicit Image URL field (handle both formats)
    # Database uses 'image_url', Excel/CSV uses 'Image URL'
    if 'Image URL' in product_info and product_info['Image URL']:
        return normalize_url(product_info['Image URL'])
    if 'image_url' in product_info and product_info['image_url']:
        return normalize_url(product_info['image_url'])
    
    # Next, check for any field that might contain an image URL
    for key, value in product_info.items():
        if isinstance(value, str) and ('image' in key.lower() or 'photo' in key.lower() or 'pic' in key.lower()):
            if is_valid_url(value):
                return normalize_url(value)
    
    # Generate a pseudo-URL based on product name/category for product images in static folder
    if product_info:
        # Get product name, category and SKU for smart image selection
        product_name = product_info.get('Product Name', '').strip()
        category = product_info.get('category', '')
        sku = product_info.get('Unique ID', '')
        
        # Try to determine image name from product characteristics
        image_name = None
        
        # Base images
        if 'B3Round' in product_name:
            image_name = 'b3round'
        elif 'B3Square' in product_name:
            image_name = 'b3square'
        elif 'shower base' in product_name.lower():
            image_name = 'b3square'  # fallback to a square base
        elif category == 'Shower Bases' or (sku and (sku.startswith('410') or sku.startswith('420'))):
            # Any shower base
            if '60' in product_name:  # 60" bases are usually round
                image_name = 'b3round'
            else:
                image_name = 'b3square'  # Default to square
                
        # Door images    
        elif 'Shower Doors' in category or 'door' in product_name.lower():
            image_name = 'shower_door'
        elif 'Tub Doors' in category:
            image_name = 'shower_door'  # Reuse shower door image
            
        # Wall images
        elif 'Walls' in category or 'wall' in product_name.lower():
            image_name = 'shower_wall'
            
        # Return panel images
        elif 'Return Panels' in category or 'return panel' in product_name.lower():
            image_name = 'return_panel'
            
        # If we identified an image to use, return its URL
        if image_name:
            logger.debug(f"Selected image '{image_name}' for product: {product_name}")
            return f"/static/images/products/{image_name}.jpg"
            
        # If we couldn't determine a specific image, fall back to a generic one by category
        if category:
            category_lower = category.lower()
            if 'base' in category_lower:
                return "/static/images/products/b3square.jpg"
            elif 'door' in category_lower:
                return "/static/images/products/shower_door.jpg"
            elif 'wall' in category_lower:
                return "/static/images/products/shower_wall.jpg"
            elif 'panel' in category_lower:
                return "/static/images/products/return_panel.jpg"
    
    # If we couldn't find or generate an image URL, return an empty string
    return ""

def normalize_url(url):
    """
    Normalize a URL to ensure it's valid and properly formatted.
    
    Args:
        url (str): The URL to normalize
        
    Returns:
        str: Normalized URL
    """
    # Handle None, empty strings, and NaN values from pandas
    if not url or not isinstance(url, str):
        return ""
    
    # Strip whitespace
    url = url.strip()
    
    # Add https:// if the URL doesn't have a scheme
    if url and not re.match(r'^https?://', url, re.IGNORECASE):
        url = 'https://' + url
    
    # URL-encode special characters
    try:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.quote(parsed.path)
        url = urllib.parse.urlunparse((
            parsed.scheme, 
            parsed.netloc, 
            path, 
            parsed.params, 
            parsed.query, 
            parsed.fragment
        ))
    except Exception as e:
        logger.warning(f"Error normalizing URL {url}: {str(e)}")
    
    return url

def is_valid_url(url):
    """
    Check if a string is a valid URL.
    
    Args:
        url (str): String to check
        
    Returns:
        bool: True if the string appears to be a URL
    """
    if not url or not isinstance(url, str):
        return False
    
    # Simple URL pattern matching
    url_pattern = re.compile(
        r'^(https?://)?' # http:// or https:// (optional)
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}' # domain
        r'(/[a-zA-Z0-9_.-]+)*/?$', # path (optional)
        re.IGNORECASE
    )
    
    return bool(url_pattern.match(url.strip()))