#!/usr/bin/env python
import pandas as pd

# List of sheets to check
sheets = ['Tub Doors', 'Shower Doors']

# Load each sheet and print columns
for sheet in sheets:
    print(f"\n{sheet} columns:")
    data = pd.read_excel('data/Product Data.xlsx', sheet_name=sheet)
    print(data.columns.tolist())
    
    # Check for Maximum Width column
    if 'Maximum Width' in data.columns:
        print(f"Sample Maximum Width value: {data.iloc[0].get('Maximum Width')}")
    
    # Print first row data for debugging
    print(f"\nFirst row sample data:")
    first_row = data.iloc[0].to_dict()
    for key, value in first_row.items():
        print(f"  {key}: {value}")