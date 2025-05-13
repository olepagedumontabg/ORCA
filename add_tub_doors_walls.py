import pandas as pd
import os

# Path to Excel file
excel_file = 'data/Product Data.xlsx'

# Read the Excel file
with pd.ExcelFile(excel_file) as xls:
    # Get all sheet names
    sheet_names = xls.sheet_names
    
    # Read all sheets into a dictionary of dataframes
    dfs = {sheet_name: pd.read_excel(xls, sheet_name) for sheet_name in sheet_names}

# Create sample tub doors data
tub_doors_data = pd.DataFrame({
    'Unique ID': ['DOOR-123', 'DOOR-456', 'DOOR-789', 'DOOR-101'],
    'Product Name': ['Sliding Tub Door 56-58', 'Pivot Tub Door 48-50', 'Bypass Tub Door 58-60', 'Folding Tub Door 45-50'],
    'Brand': ['Maax', 'Swan', 'Maax', 'Bootz'],
    'Series': ['Professional', 'Retail', 'MAAX', 'Collection'],
    'Family': ['Exhibit', 'Olio', 'Nomad', 'Vellamo'],
    'Nominal Dimensions': ['58 x 60', '48 x 60', '60 x 60', '50 x 60'],
    'Minimum Width': [56, 48, 58, 45],
    'Maximum Width': [58, 50, 60, 50],
    'Glass Thickness': ['8mm', '6mm', '8mm', '6mm'],
    'Door Type': ['Sliding', 'Pivot', 'Bypass', 'Folding'],
    'Ranking': [1, 2, 3, 4]
})

# Create sample walls data
walls_data = pd.DataFrame({
    'Unique ID': ['WALL-123', 'WALL-456', 'WALL-789'],
    'Product Name': ['Alcove Tub Wall 60x32', 'Corner Tub Wall 60x60', 'Rectangular Tub Wall 48x32'],
    'Brand': ['Maax', 'Swan', 'Bootz'],
    'Series': ['Professional', 'Retail', 'MAAX'],
    'Family': ['Utile', 'Olio', 'Nextile'],
    'Type': ['Tub Surround', 'Tub Corner', 'Tub Surround'],
    'Nominal Dimensions': ['60 x 32', '60 x 60', '48 x 32'],
    'Length': [60, 60, 48],
    'Width': [32, 60, 32],
    'Cut to Size': ['Yes', 'No', 'Yes']
})

# Update the sheets
dfs['Tub Doors'] = tub_doors_data
dfs['Walls'] = pd.concat([dfs['Walls'], walls_data], ignore_index=True)

# Write back to Excel
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    for sheet_name, df in dfs.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Added {len(tub_doors_data)} sample tub doors and {len(walls_data)} sample walls to the Excel file.")
