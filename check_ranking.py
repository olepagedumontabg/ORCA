import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ranking_check')

def check_excel_ranking(file_path='data/Product Data.xlsx'):
    """Check if the Excel file has a Ranking column in each sheet"""
    
    # Print file path for verification
    logger.info(f"Checking Excel file: {file_path}")
    
    try:
        # Load the Excel file
        xls = pd.ExcelFile(file_path)
        
        # Check each sheet
        for sheet_name in xls.sheet_names:
            logger.info(f"\nChecking sheet: {sheet_name}")
            
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Check if Ranking column exists
            if 'Ranking' in df.columns:
                logger.info(f"√ Ranking column found in {sheet_name}")
                
                # Check for non-null values
                non_null_count = df['Ranking'].count()
                total_rows = len(df)
                logger.info(f"  - {non_null_count} out of {total_rows} rows have Ranking values")
                
                # Show the first few ranking values
                if non_null_count > 0:
                    # Display the first 5 rows with ranking values
                    ranked_rows = df[df['Ranking'].notna()].head(5)
                    logger.info("  - Sample ranking values:")
                    for idx, row in ranked_rows.iterrows():
                        logger.info(f"    SKU: {row.get('Unique ID', 'N/A')}, Name: {row.get('Product Name', 'N/A')}, Ranking: {row['Ranking']} (Type: {type(row['Ranking'])})")
                    
                    # Check specifically for Duel and Duel Alto
                    duel_rows = df[df['Product Name'].str.contains('Duel', na=False)]
                    if not duel_rows.empty:
                        logger.info("  - Duel door rankings:")
                        for idx, row in duel_rows.iterrows():
                            ranking = row.get('Ranking', 'N/A')
                            logger.info(f"    SKU: {row.get('Unique ID', 'N/A')}, Name: {row.get('Product Name', 'N/A')}, Ranking: {ranking} (Type: {type(ranking)})")
            else:
                logger.info(f"× No Ranking column in {sheet_name}")
    
    except Exception as e:
        logger.error(f"Error checking Excel file: {str(e)}")

if __name__ == "__main__":
    check_excel_ranking()