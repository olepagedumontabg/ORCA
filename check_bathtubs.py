#!/usr/bin/env python
import pandas as pd

# Load the Excel file
try:
    # Try to load the bathtubs and shower bases sheets
    sheets = ['Bathtubs', 'Shower Bases']
    
    print("Checking Excel file for Max Door Width information:")
    for sheet_name in sheets:
        print(f"\n{sheet_name} columns:")
        try:
            data = pd.read_excel('data/Product Data.xlsx', sheet_name=sheet_name)
            print(data.columns.tolist())
            
            # Check for any column related to door width
            width_columns = [col for col in data.columns if 'width' in col.lower() or 'door' in col.lower()]
            if width_columns:
                print(f"Potential door width columns: {width_columns}")
                
            # Print first row as sample
            if not data.empty:
                print("\nSample data (first row):")
                first_row = data.iloc[0].to_dict()
                for key, value in first_row.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error loading {sheet_name}: {e}")
    
except Exception as e:
    print(f"Error: {e}")