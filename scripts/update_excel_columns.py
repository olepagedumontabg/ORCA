#!/usr/bin/env python
"""
Script to add Glass Thickness and Door Type columns to the Product Data Excel file.
This helps the compatibility finder application filter products more effectively.
"""

import os
import pandas as pd
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_glass_thickness(name):
    """
    Extract glass thickness from product name
    
    Args:
        name (str): Product name to extract from
        
    Returns:
        str: Extracted thickness (e.g. '6mm') or empty string if not found
    """
    if not name or not isinstance(name, str):
        return ''
    
    match = re.search(r'(\d+)[\s-]*mm', str(name).lower())
    if match:
        return match.group(1) + 'mm'
    return ''

def determine_door_type(name):
    """
    Determine door type based on product name patterns
    
    Args:
        name (str): Product name to analyze
        
    Returns:
        str: Door type classification
    """
    if not name or not isinstance(name, str):
        return 'Standard'
    
    name = name.lower()
    
    if 'sliding' in name:
        return 'Sliding'
    elif 'pivot' in name:
        return 'Pivot'
    elif 'hinged' in name or 'swing' in name:
        return 'Hinged/Swing'
    elif 'bypass' in name:
        return 'Bypass'
    elif 'corner' in name:
        return 'Corner'
    elif 'round' in name:
        return 'Round'
    elif 'square' in name:
        return 'Square'
    
    return 'Standard'

def update_excel_columns(file_path):
    """
    Add Glass Thickness and Door Type columns to the Excel file
    
    Args:
        file_path (str): Path to the Excel file
    """
    try:
        logger.info(f"Loading Excel file: {file_path}")
        
        # Try to read the Excel file
        try:
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception as e:
            logger.warning(f"Failed to read with openpyxl engine, trying xlrd: {str(e)}")
            excel_file = pd.ExcelFile(file_path, engine='xlrd')
        
        # Create a writer to save the modified sheets
        writer = pd.ExcelWriter('data/Product Data - Updated.xlsx', engine='openpyxl')
        
        # Process each sheet
        for sheet_name in excel_file.sheet_names:
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Read the sheet
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd')
                except Exception as e:
                    logger.error(f"Failed to read sheet {sheet_name}: {str(e)}")
                    continue
            
            # Only add Glass Thickness and Door Type columns to the Shower Doors sheet
            if sheet_name == 'Shower Doors':
                # Add Glass Thickness column if it doesn't exist
                if 'Glass Thickness' not in df.columns:
                    df['Glass Thickness'] = df['Product Name'].apply(extract_glass_thickness)
                    logger.info("Added Glass Thickness column")
                
                # Add Door Type column if it doesn't exist
                if 'Door Type' not in df.columns:
                    df['Door Type'] = df['Product Name'].apply(determine_door_type)
                    logger.info("Added Door Type column")
            
            # Write the modified sheet back to the Excel file
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Save the Excel file
        writer.close()
        logger.info("Excel file updated successfully")
        
        # Replace the original file with the updated one
        os.replace('data/Product Data - Updated.xlsx', file_path)
        logger.info("Original file replaced with updated version")
        
    except Exception as e:
        logger.error(f"Error updating Excel file: {str(e)}")

if __name__ == '__main__':
    # Get the path to the Excel file
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'Product Data.xlsx')
    
    # Update the Excel file
    update_excel_columns(excel_path)