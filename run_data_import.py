"""
Import Data Script
Run this script to import data from Excel files and process compatibility.
"""
import os
import sys
import logging
from data_updater import run_update_process
from compatibility_processor import run_compatibility_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('data_import')

def main():
    # Check if the DATABASE_URL environment variable is set
    if not os.environ.get('DATABASE_URL'):
        logger.error("DATABASE_URL environment variable not set")
        logger.error("Please make sure the database is configured properly")
        return False
    
    # Check if we have any data files
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    excel_files = [f for f in os.listdir(data_path) if f.endswith('.xlsx')]
    
    if not excel_files:
        logger.error(f"No Excel files found in {data_path}")
        logger.error("Please place your product data Excel files in the /data folder")
        return False
    
    logger.info(f"Found {len(excel_files)} Excel files in data directory")
    
    # Run the update process to load data into database
    logger.info("Step 1: Loading Excel data into database...")
    run_update_process()
    
    # Run the compatibility processor
    logger.info("Step 2: Processing compatibility relationships...")
    run_compatibility_processor()
    
    logger.info("Data import complete!")
    return True

if __name__ == "__main__":
    main()