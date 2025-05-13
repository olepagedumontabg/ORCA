import pandas as pd
import os

# Create a directory for test data if it doesn't exist
os.makedirs('data/test', exist_ok=True)

# Create test data
test_bathtubs = pd.DataFrame([
    {
        'Unique ID': 'BTH-001',
        'Product Name': 'Test Alcove Bathtub 60x32',
        'Deck Width': 2.5,
        'Max Door Width': 58.5,
        'Nominal Dimensions': '60 x 32',
        'Length': 60,
        'Width': 32,
        'Installation': 'Alcove',
        'Brand': 'Maax',
        'Series': 'MAAX',
        'Family': 'Utile',
        'Compatible Doors': None,
        'Compatible Walls': None
    },
    {
        'Unique ID': 'BTH-002',
        'Product Name': 'Test Corner Bathtub 60x60',
        'Deck Width': 3.0,
        'Max Door Width': 57.0,
        'Nominal Dimensions': '60 x 60',
        'Length': 60,
        'Width': 60,
        'Installation': 'Corner',
        'Brand': 'Swan',
        'Series': 'Swan',  # Changed from Retail to Swan for better compatibility
        'Family': 'Tub Surround',
        'Compatible Doors': None,
        'Compatible Walls': None
    }
])

# Create test tub doors data
test_tub_doors = pd.DataFrame([
    {
        'Unique ID': 'TDR-001',
        'Product Name': 'Test Sliding Tub Door 56-59',
        'Required Deck Width': 2.0,
        'Minimum Width': 56.0,
        'Maximum Width': 59.0,
        'Maximum Height': 58.0,
        'Brand': 'Maax',
        'Series': 'MAAX',
        'Family': 'Revelation',
        'Ranking': 1000,
        'Glass Thickness': '8mm',
        'Door Type': 'Sliding'
    },
    {
        'Unique ID': 'TDR-002',
        'Product Name': 'Test Pivot Tub Door 58-60',
        'Required Deck Width': 3.0,
        'Minimum Width': 58.0,
        'Maximum Width': 60.0,
        'Maximum Height': 59.0,
        'Brand': 'Maax',
        'Series': 'Professional',
        'Family': 'Kleara',
        'Ranking': 950,
        'Glass Thickness': '6mm',
        'Door Type': 'Pivot'
    }
])

# Create test walls data
test_walls = pd.DataFrame([
    {
        'Unique ID': 'WLL-001',
        'Product Name': 'Test Alcove Tub Wall Kit 60x32',
        'Image URL': None,
        'Nominal Dimensions': '60 x 32',
        'Length': 60,
        'Width': 32,
        'Type': 'Alcove Tub Wall Kit',
        'Cut to Size': 'Yes',
        'Brand': 'Maax',
        'Series': 'Retail',
        'Family': 'Utile',
        'Ranking': 1100
    },
    {
        'Unique ID': 'WLL-002',
        'Product Name': 'Test Corner Tub Wall Kit 60x60',
        'Image URL': None,
        'Nominal Dimensions': '60 x 60',
        'Length': 60,
        'Width': 60,
        'Type': 'Corner Tub Wall Kit',
        'Cut to Size': 'No',
        'Brand': 'Swan',
        'Series': 'Swan',
        'Family': 'Tub Surround',
        'Ranking': 1200
    },
    {
        'Unique ID': 'WLL-003',
        'Product Name': 'Test Alcove Tub Wall Kit Maax',
        'Image URL': None,
        'Nominal Dimensions': '60 x 32',
        'Length': 60,
        'Width': 32,
        'Type': 'Alcove Tub Wall Kit',
        'Cut to Size': 'Yes',
        'Brand': 'Maax',
        'Series': 'MAAX',
        'Family': 'Utile',
        'Ranking': 950
    }
])

# Save test data to Excel
with pd.ExcelWriter('data/test/test_product_data.xlsx') as writer:
    test_bathtubs.to_excel(writer, sheet_name='Bathtubs', index=False)
    test_tub_doors.to_excel(writer, sheet_name='Tub Doors', index=False)
    test_walls.to_excel(writer, sheet_name='Walls', index=False)

print("Test data created successfully in data/test/test_product_data.xlsx")
print("Use this file for testing the bathtub compatibility functionality.")