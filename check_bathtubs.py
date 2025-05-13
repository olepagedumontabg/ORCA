import pandas as pd

# Load the Excel file
try:
    # Bathtubs
    print("BATHTUBS SHEET INFO:")
    bathtubs = pd.read_excel('data/Product Data.xlsx', sheet_name='Bathtubs')
    print(f"Number of rows: {len(bathtubs)}")
    
    if len(bathtubs) > 0:
        print("\nFirst 3 rows:")
        for i in range(min(3, len(bathtubs))):
            unique_id = bathtubs.iloc[i].get('Unique ID', 'No ID')
            name = bathtubs.iloc[i].get('Product Name', 'No Name')
            print(f"{unique_id} - {name}")
    else:
        print("No data in Bathtubs sheet")
    
except Exception as e:
    print(f"Error: {e}")