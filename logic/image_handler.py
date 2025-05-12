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
        
    # First, check if we have an explicit Image URL field
    if 'Image URL' in product_info and product_info['Image URL']:
        return normalize_url(product_info['Image URL'])
    
    # Next, check for any field that might contain an image URL
    for key, value in product_info.items():
        if isinstance(value, str) and ('image' in key.lower() or 'photo' in key.lower() or 'pic' in key.lower()):
            if is_valid_url(value):
                return normalize_url(value)
    
    # Generate a pseudo-URL based on product name for product images in static folder
    if 'Product Name' in product_info and product_info['Product Name']:
        product_name = product_info['Product Name'].strip()
        # Convert product name to a format suitable for a file name
        product_name = product_name.lower().replace(' ', '_').replace('-', '_')
        # Remove any other special characters
        import re
        product_name = re.sub(r'[^a-z0-9_]', '', product_name)
        
        # Check if this category has common image patterns
        category = product_info.get('category', '')
        sku = product_info.get('Unique ID', '')
        
        # Try to determine image name from product type
        image_name = None
        if 'B3Round' in product_info.get('Product Name', ''):
            image_name = 'b3round'
        elif 'B3Square' in product_info.get('Product Name', ''):
            image_name = 'b3square'
        elif 'shower base' in product_info.get('Product Name', '').lower():
            image_name = 'shower_base'
        elif 'shower door' in category.lower() or 'door' in product_info.get('Product Name', '').lower():
            image_name = 'shower_door'
            
        if image_name:
            return f"/static/images/products/{image_name}.jpg"
    
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
    if not url:
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