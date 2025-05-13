import pandas as pd
import os
import logging
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ranking_adder')

def add_ranking_column(file_path='data/Product Data.xlsx'):
    """Add a Ranking column to specific sheets in the Excel file"""
    
    # Print file path for verification
    logger.info(f"Adding Ranking column to Excel file: {file_path}")
    
    # Create a backup of the file first
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup at: {backup_path}")
    
    try:
        # Dictionary to store DataFrames from all sheets
        dfs = {}
        
        # Load all sheets
        xls = pd.ExcelFile(file_path)
        for sheet_name in xls.sheet_names:
            dfs[sheet_name] = pd.read_excel(file_path, sheet_name=sheet_name)
            
        # Add ranking to Shower Doors
        if 'Shower Doors' in dfs:
            df = dfs['Shower Doors']
            logger.info(f"Adding Ranking column to Shower Doors")
            
            # First check if Ranking column already exists
            if 'Ranking' not in df.columns:
                # Add Ranking column with default value
                df['Ranking'] = 999
                
                # Define specific rankings for products we know about
                rankings = {
                    # Duel doors with specific ranking values - process in exact order!
                    'Duel Alto': 1725,  # Must be before 'Duel' to handle specific model first
                    'Duel': 1750,
                    # Add more product name patterns and rankings as needed
                    'Capella': 1800,
                    'Reveal': 1850,
                    'Halo': 1900,
                    'Uptown': 2000,
                    'Connect': 2100,
                    'Nebula': 2200,
                }
                
                # Manual handling for Duel Alto vs Duel to avoid overlapping matches
                duel_alto_mask = df['Product Name'].str.contains('Duel Alto', case=False, na=False)
                duel_mask = df['Product Name'].str.contains('Duel', case=False, na=False) & ~duel_alto_mask

                # Apply Duel Alto ranking
                if duel_alto_mask.any():
                    count = duel_alto_mask.sum()
                    logger.info(f"  Assigning ranking 1725 to {count} products matching 'Duel Alto'")
                    df.loc[duel_alto_mask, 'Ranking'] = 1725
                
                # Apply Duel (not Alto) ranking
                if duel_mask.any():
                    count = duel_mask.sum()
                    logger.info(f"  Assigning ranking 1750 to {count} products matching 'Duel' (not Alto)")
                    df.loc[duel_mask, 'Ranking'] = 1750
                
                # Apply other rankings based on product name matches
                for name_pattern, rank in rankings.items():
                    # Skip Duel patterns as we handled them separately
                    if name_pattern in ['Duel', 'Duel Alto']:
                        continue
                        
                    # Use case-insensitive contains to find matching products
                    mask = df['Product Name'].str.contains(name_pattern, case=False, na=False)
                    if mask.any():
                        count = mask.sum()
                        logger.info(f"  Assigning ranking {rank} to {count} products matching '{name_pattern}'")
                        df.loc[mask, 'Ranking'] = rank
                
                # Update the dictionary with the modified DataFrame
                dfs['Shower Doors'] = df
            else:
                logger.info("Ranking column already exists in Shower Doors")
        
        # Also add ranking to other sheets like Tub Doors, Screens, Walls
        for sheet_name in ['Tub Doors', 'Screens', 'Walls', 'Enclosures']:
            if sheet_name in dfs:
                df = dfs[sheet_name]
                logger.info(f"Adding Ranking column to {sheet_name}")
                
                # Check if Ranking column already exists
                if 'Ranking' not in df.columns:
                    # Add Ranking column with default value
                    df['Ranking'] = 999
                    
                    # Update the dictionary with the modified DataFrame
                    dfs[sheet_name] = df
                else:
                    logger.info(f"Ranking column already exists in {sheet_name}")
        
        # Create a temporary path for writing with proper extension
        temp_path = f"{file_path}.new.xlsx"
        
        # Write all sheets to a new Excel file
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Replace the original file with the new one
        os.replace(temp_path, file_path)
        logger.info(f"Successfully saved file with new Ranking columns to {file_path}")
    
    except Exception as e:
        logger.error(f"Error adding Ranking column: {str(e)}")
        # Try to restore from backup
        if os.path.exists(backup_path):
            os.replace(backup_path, file_path)
            logger.info(f"Restored original file from backup {backup_path}")

if __name__ == "__main__":
    add_ranking_column()