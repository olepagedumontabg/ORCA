
import os
import sys
import pandas as pd

# Adjust the paths for our environment
workbook_path = os.path.join('data', 'test_base_doors.xlsx')
print(f"Using workbook: {workbook_path}")

# Now import and run the compatibility script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scripts.base_doors_walls import match_compatibility

# Run the compatibility function
match_compatibility()
print("Base-Doors-Walls compatibility processing complete!")
