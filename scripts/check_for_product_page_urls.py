"""
Script to check if any products in the Excel file have Product Page URL values
"""

import pandas as pd
import os

def check_for_product_page_urls():
    """Check if any products in the Excel file have Product Page URL values"""
    
    data_file = 'data/Product Data.xlsx'
    
    if not os.path.exists(data_file):
        print(f"Error: Could not find {data_file}")
        return
    
    print(f"Checking {data_file} for Product Page URL values...")
    
    # Try with different Excel engines
    try:
        excel_file = pd.ExcelFile(data_file, engine='openpyxl')
    except Exception as e:
        print(f"Error with openpyxl: {e}")
        try:
            excel_file = pd.ExcelFile(data_file, engine='xlrd')
        except Exception as e:
            print(f"Error with xlrd: {e}")
            return
    
    sheets = excel_file.sheet_names
    urls_found = 0
    
    for sheet in sheets:
        try:
            df = pd.read_excel(data_file, sheet_name=sheet, engine='openpyxl')
        except Exception:
            try:
                df = pd.read_excel(data_file, sheet_name=sheet, engine='xlrd')
            except Exception as e:
                print(f"Error reading sheet {sheet}: {e}")
                continue
        
        # Check if "Product Page URL" column exists
        if "Product Page URL" in df.columns:
            # Count non-null values
            non_null_urls = df["Product Page URL"].dropna().count()
            if non_null_urls > 0:
                print(f"Sheet {sheet}: Found {non_null_urls} products with Product Page URL values")
                
                # Print a few examples
                sample = df[df["Product Page URL"].notna()].head(3)
                for i, row in sample.iterrows():
                    print(f"  SKU: {row.get('Unique ID', 'Unknown')}, URL: {row['Product Page URL']}")
                
                urls_found += non_null_urls
            else:
                print(f"Sheet {sheet}: No Product Page URL values found")
        else:
            print(f"Sheet {sheet}: No Product Page URL column found")
    
    if urls_found == 0:
        print("\nNo Product Page URL values found in any sheet. Please check if the column exists and has values.")
        print("If the column doesn't exist, you may need to add it to the Excel file.")
    else:
        print(f"\nFound a total of {urls_found} products with Product Page URL values")

if __name__ == '__main__':
    check_for_product_page_urls()