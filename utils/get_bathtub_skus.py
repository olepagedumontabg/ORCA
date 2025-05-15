import pandas as pd

# Load the bathtubs sheet from Excel
try:
    df = pd.read_excel('data/Product Data.xlsx', sheet_name='Bathtubs')
    print("First 5 bathtub SKUs:")
    
    # Extract the first 5 rows
    for i in range(min(5, len(df))):
        unique_id = df.iloc[i].get('Unique ID', 'No ID')
        name = df.iloc[i].get('Product Name', 'No Name')
        print(f"{unique_id} - {name}")
        
except Exception as e:
    print(f"Error: {e}")