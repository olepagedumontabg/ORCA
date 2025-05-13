import pandas as pd
import os

# Check if data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

# Path to Excel file
excel_file = 'data/Product Data.xlsx'

# Read the Excel file
with pd.ExcelFile(excel_file) as xls:
    # Get all sheet names
    sheet_names = xls.sheet_names
    
    # Read all sheets into a dictionary of dataframes
    dfs = {sheet_name: pd.read_excel(xls, sheet_name) for sheet_name in sheet_names}

# Create sample bathtub data
bathtub_data = pd.DataFrame({
    'Unique ID': ['BTB-123456', 'BTB-234567', 'BTB-345678'],
    'Product Name': ['Luxe Alcove Bathtub 60x32', 'Classic Drop-in Tub 48x32', 'Premium Corner Tub 60x60'],
    'Brand': ['Maax', 'Swan', 'Bootz'],
    'Series': ['Professional', 'Retail', 'MAAX'],
    'Family': ['Exhibit', 'Olio', 'Vellamo'],
    'Nominal Dimensions': ['60 x 32', '48 x 32', '60 x 60'],
    'Length': [60, 48, 60],
    'Width': [32, 32, 60],
    'Max Door Width': [58, 46, 58],
    'Installation': ['Alcove', 'Drop-in', 'Corner']
})

# Update the bathtubs sheet
dfs['Bathtubs'] = bathtub_data

# Write back to Excel
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    for sheet_name, df in dfs.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Added {len(bathtub_data)} sample bathtubs to the Excel file.")
