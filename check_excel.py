#!/usr/bin/env python
import pandas as pd
import sys

try:
    data = pd.read_excel('attached_assets/Product Data_05_14_2025.xlsx', sheet_name=None)
    print(f"Successfully loaded excel file. Found sheets: {list(data.keys())}")
    
    if 'Bathtubs' in data:
        bathtubs = data['Bathtubs']
        print(f"Bathtubs sheet found with {len(bathtubs)} rows")
        print("First few rows:")
        print(bathtubs.head(3))
    else:
        print("Bathtubs sheet not found!")
        
except Exception as e:
    print(f"Error reading Excel file: {e}")