"""
Verify that Duel Alto doors have lower ranking than regular Duel doors
"""
import logging
import sys
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("duel_verify")

def verify_duel_ranking(file_path="data/Product Data.xlsx"):
    """Verify that Duel Alto products have lower ranking than regular Duel products"""
    logger.info(f"Loading Excel file from {file_path}")
    
    try:
        # Load the Shower Doors sheet
        doors_df = pd.read_excel(file_path, sheet_name="Shower Doors")
        
        # Check if Ranking column exists
        if "Ranking" not in doors_df.columns:
            logger.error("No Ranking column found in Shower Doors sheet")
            return False
            
        # Filter for Duel products
        duel_alto_df = doors_df[doors_df["Product Name"].str.contains("Duel Alto", na=False)]
        duel_regular_df = doors_df[
            doors_df["Product Name"].str.contains("Duel", na=False) & 
            ~doors_df["Product Name"].str.contains("Duel Alto", na=False)
        ]
        
        # Check if we found any products
        if duel_alto_df.empty:
            logger.warning("No Duel Alto products found")
        else:
            logger.info(f"Found {len(duel_alto_df)} Duel Alto products")
            for idx, row in duel_alto_df.iterrows():
                logger.info(f"Duel Alto: {row['Unique ID']} - {row['Product Name']} - Ranking: {row['Ranking']}")
                
        if duel_regular_df.empty:
            logger.warning("No regular Duel products found")
        else:
            logger.info(f"Found {len(duel_regular_df)} regular Duel products")
            for idx, row in duel_regular_df.iterrows():
                logger.info(f"Duel (regular): {row['Unique ID']} - {row['Product Name']} - Ranking: {row['Ranking']}")
        
        # Verify that all Duel Alto products have lower ranking than all regular Duel products
        if not duel_alto_df.empty and not duel_regular_df.empty:
            alto_rankings = duel_alto_df["Ranking"].unique()
            regular_rankings = duel_regular_df["Ranking"].unique()
            
            logger.info(f"Duel Alto rankings: {alto_rankings}")
            logger.info(f"Regular Duel rankings: {regular_rankings}")
            
            all_lower = True
            for alto_rank in alto_rankings:
                for reg_rank in regular_rankings:
                    if alto_rank >= reg_rank:
                        logger.error(f"Error: Duel Alto rank {alto_rank} is not lower than regular Duel rank {reg_rank}")
                        all_lower = False
            
            if all_lower:
                logger.info("✓ SUCCESS: All Duel Alto products have lower ranking than regular Duel products")
                return True
            else:
                logger.error("✗ FAILED: Some Duel Alto products do not have lower ranking than regular Duel products")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying Duel rankings: {str(e)}")
        return False

if __name__ == "__main__":
    verify_duel_ranking()