import pandas as pd
import os
import logging
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ranking_fixer')

def fix_duel_rankings(file_path='data/Product Data.xlsx'):
    """Fix the rankings for Duel and Duel Alto products"""
    
    logger.info(f"Fixing Duel rankings in Excel file: {file_path}")
    
    # Create a backup of the file first
    backup_path = f"{file_path}.duel_fix.bak"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup at: {backup_path}")
    
    try:
        # Load the Shower Doors sheet
        logger.info("Loading Shower Doors sheet")
        shower_doors_df = pd.read_excel(file_path, sheet_name='Shower Doors')
        
        # Create masks for Duel Alto and regular Duel products
        duel_alto_mask = shower_doors_df['Product Name'].str.contains('Duel Alto', case=False, na=False)
        duel_regular_mask = shower_doors_df['Product Name'].str.contains('Duel', case=False, na=False) & ~duel_alto_mask
        
        # Print current rankings
        logger.info("Current rankings:")
        for idx, row in shower_doors_df[duel_alto_mask].iterrows():
            logger.info(f"Duel Alto - SKU: {row['Unique ID']}, Name: {row['Product Name']}, Ranking: {row.get('Ranking', 'N/A')}")
        
        for idx, row in shower_doors_df[duel_regular_mask].iterrows():
            logger.info(f"Duel (not Alto) - SKU: {row['Unique ID']}, Name: {row['Product Name']}, Ranking: {row.get('Ranking', 'N/A')}")
        
        # Fix rankings
        if 'Ranking' in shower_doors_df.columns:
            # Set Duel Alto ranking (lower value so it appears first)
            shower_doors_df.loc[duel_alto_mask, 'Ranking'] = 1725
            logger.info(f"Set Ranking=1725 for {duel_alto_mask.sum()} Duel Alto products")
            
            # Set regular Duel ranking
            shower_doors_df.loc[duel_regular_mask, 'Ranking'] = 1750
            logger.info(f"Set Ranking=1750 for {duel_regular_mask.sum()} regular Duel products")
            
            # Print updated rankings
            logger.info("Updated rankings:")
            for idx, row in shower_doors_df[duel_alto_mask].iterrows():
                logger.info(f"Duel Alto - SKU: {row['Unique ID']}, Name: {row['Product Name']}, Ranking: {row.get('Ranking', 'N/A')}")
            
            for idx, row in shower_doors_df[duel_regular_mask].iterrows():
                logger.info(f"Duel (not Alto) - SKU: {row['Unique ID']}, Name: {row['Product Name']}, Ranking: {row.get('Ranking', 'N/A')}")
        else:
            logger.error("No Ranking column found in Shower Doors sheet")
            return
            
        # Load all sheets from the Excel file
        logger.info("Loading all sheets")
        xls = pd.ExcelFile(file_path)
        all_sheets = {}
        for sheet_name in xls.sheet_names:
            if sheet_name == 'Shower Doors':
                all_sheets[sheet_name] = shower_doors_df
            else:
                all_sheets[sheet_name] = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Create a temporary path for writing
        temp_path = f"{file_path}.new.xlsx"
        
        # Write all sheets to a new Excel file
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            for sheet_name, df in all_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Replace the original file with the new one
        os.replace(temp_path, file_path)
        logger.info(f"Successfully saved file with fixed Duel rankings to {file_path}")
        
        # Force the server to reload the data
        logger.info("Updating the in-memory data cache")
        try:
            # Import locally in case it wasn't available at module load time
            import data_update_service as data_service
            # Update the global cache
            data_service.update_data()
            logger.info("Triggered data update service to reload data")
        except Exception as e:
            logger.error(f"Error updating in-memory cache: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error fixing Duel rankings: {str(e)}")
        # Try to restore from backup
        if os.path.exists(backup_path):
            os.replace(backup_path, file_path)
            logger.info(f"Restored original file from backup {backup_path}")

if __name__ == "__main__":
    fix_duel_rankings()