import pandas as pd

# Load the Excel file
try:
    # Tub Doors
    print("COLUMNS IN TUB DOORS SHEET:")
    tub_doors = pd.read_excel('data/Product Data.xlsx', sheet_name='Tub Doors')
    print(list(tub_doors.columns))
    print("\nSample data (first row):")
    if not tub_doors.empty:
        print(tub_doors.iloc[0].to_dict())
    else:
        print("No data in Tub Doors sheet")
    
    print("\n" + "-"*80 + "\n")
    
    # Bathtubs
    print("COLUMNS IN BATHTUBS SHEET:")
    bathtubs = pd.read_excel('data/Product Data.xlsx', sheet_name='Bathtubs')
    print(list(bathtubs.columns))
    print("\nSample data (first row):")
    if not bathtubs.empty:
        print(bathtubs.iloc[0].to_dict())
    else:
        print("No data in Bathtubs sheet")
    
    print("\n" + "-"*80 + "\n")
    
    # Walls
    print("COLUMNS IN WALLS SHEET:")
    walls = pd.read_excel('data/Product Data.xlsx', sheet_name='Walls')
    print(list(walls.columns))
    print("\nSample data (first row):")
    if not walls.empty:
        print(walls.iloc[0].to_dict())
    else:
        print("No data in Walls sheet")
    
except Exception as e:
    print(f"Error: {e}")