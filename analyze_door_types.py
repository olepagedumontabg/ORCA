#!/usr/bin/env python
"""
Script to analyze door types in the Excel data.
"""

import os
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_door_types():
    """
    Analyze door types in the Excel file
    """
    try:
        # Get the path to the Excel file
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Product Data.xlsx')
        logger.info(f"Analyzing Excel file: {file_path}")
        
        # Try to read the Excel file
        try:
            excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception as e:
            logger.warning(f"Failed to read with openpyxl engine, trying xlrd: {str(e)}")
            excel_file = pd.ExcelFile(file_path, engine='xlrd')
        
        # Check if Shower Doors sheet exists
        if 'Shower Doors' in excel_file.sheet_names:
            logger.info("Found Shower Doors sheet")
            
            # Read the sheet
            try:
                df = pd.read_excel(file_path, sheet_name='Shower Doors', engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(file_path, sheet_name='Shower Doors', engine='xlrd')
                except Exception as e:
                    logger.error(f"Failed to read Shower Doors sheet: {str(e)}")
                    return
            
            # Check if Door Type column exists
            if 'Door Type' in df.columns:
                logger.info("Found Door Type column")
                
                # Get unique door types
                door_types = df['Door Type'].dropna().unique()
                logger.info(f"Found {len(door_types)} unique door types:")
                for door_type in sorted(door_types):
                    logger.info(f"  - {door_type}")
                
                # Count occurrences of each door type
                door_type_counts = df['Door Type'].value_counts().sort_values(ascending=False)
                logger.info("\nDoor type counts:")
                for door_type, count in door_type_counts.items():
                    logger.info(f"  - {door_type}: {count}")
            else:
                logger.info("Door Type column not found")
        else:
            logger.info("Shower Doors sheet not found")
            
    except Exception as e:
        logger.error(f"Error analyzing Excel file: {str(e)}")

if __name__ == '__main__':
    analyze_door_types()