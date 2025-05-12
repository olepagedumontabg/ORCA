#!/usr/bin/env python3
"""
Script to add an Image URL column to the Product Data Excel file.
This helps the compatibility finder application display product images.
"""

import os
import pandas as pd
import sys
from pathlib import Path

def add_image_url_column(excel_path):
    """
    Add an Image URL column to all worksheets in the Excel file
    
    Args:
        excel_path (str): Path to the Excel file
    """
    try:
        print(f"Opening Excel file: {excel_path}")
        
        # Use ExcelFile to get all sheet names, explicitly specify engine
        xl = pd.ExcelFile(excel_path, engine='openpyxl')
        sheet_names = xl.sheet_names
        print(f"Found {len(sheet_names)} sheets: {sheet_names}")
        
        # Create a backup first
        backup_path = excel_path + '.backup'
        import shutil
        shutil.copy2(excel_path, backup_path)
        print(f"Created backup at {backup_path}")
        
        # Initialize ExcelWriter for saving changes
        writer = pd.ExcelWriter(excel_path, engine='openpyxl')
        
        # Process each sheet
        for sheet in sheet_names:
            print(f"\nProcessing sheet: {sheet}")
            
            # Read the entire sheet
            df = pd.read_excel(excel_path, sheet_name=sheet, engine='openpyxl')
            
            # Check if Image URL column already exists
            if 'Image URL' in df.columns:
                print(f"Image URL column already exists in {sheet}")
            else:
                # Add empty Image URL column
                df['Image URL'] = ''
                print(f"Added Image URL column to {sheet}")
            
            # Write the updated dataframe back to the Excel file
            df.to_excel(writer, sheet_name=sheet, index=False)
        
        # Save the Excel file
        writer.close()
        print(f"\nSuccessfully updated {excel_path}")
        print("\nNow you can open the Excel file and add image URLs for your products.")
        print("After adding URLs, save the Excel file and restart the application.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Find the data directory relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')
    
    # Default Excel file path
    default_excel_path = os.path.join(data_dir, 'Product Data.xlsx')
    
    # Check if a custom path was provided as a command-line argument
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        excel_path = default_excel_path
    
    # Make sure the file exists
    if not os.path.exists(excel_path):
        print(f"Error: File not found: {excel_path}")
        sys.exit(1)
    
    # Run the function
    exit_code = add_image_url_column(excel_path)
    sys.exit(exit_code)