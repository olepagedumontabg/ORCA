#!/usr/bin/env python
import pandas as pd
import os
import sys

def check_excel_file(file_path):
    """
    Check if an Excel file is valid and print its content details
    """
    print(f"Checking Excel file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File does not exist at {file_path}")
        return False
    
    try:
        # Try to read the Excel file
        df_dict = pd.read_excel(file_path, sheet_name=None)
        print(f"Successfully read the Excel file!")
        
        # Print the sheets in the file
        print(f"Sheets in the file: {list(df_dict.keys())}")
        
        # Print details about each sheet
        for sheet_name, sheet_data in df_dict.items():
            print(f"{sheet_name}: {len(sheet_data)} rows, {len(sheet_data.columns)} columns")
            print(f"Column names: {sheet_data.columns.tolist()}")
            
        # If Bathtubs sheet exists, print a sample
        if 'Bathtubs' in df_dict:
            print("\nBathtubs sample:")
            bathtubs_df = df_dict['Bathtubs']
            print(bathtubs_df.head(2))
            
            # Check if "Max Door Width" column exists
            if 'Max Door Width' in bathtubs_df.columns:
                print("\nSample 'Max Door Width' values for bathtubs:")
                sample_rows = bathtubs_df.head(5)
                for idx, row in sample_rows.iterrows():
                    sku = row.get('Unique ID', 'Unknown')
                    width = row.get('Max Door Width', 'N/A')
                    print(f"  SKU: {sku}, Max Door Width: {width}")
            else:
                print("\nWarning: 'Max Door Width' column missing from Bathtubs sheet")
            
        return True
        
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return False

if __name__ == "__main__":
    # Try both the provided file and the current data file
    files_to_check = [
        'attached_assets/Product Data_05_14_2025.xlsx',  # The provided file
        'data/Product Data.xlsx'  # The current data file
    ]
    
    for file_path in files_to_check:
        print("\n" + "="*80)
        print(f"Examining file: {file_path}")
        print("="*80)
        check_excel_file(file_path)