"""
Run the compatibility processor to generate compatibility data for the database.
This script loads data from Excel files, processes compatibility, and stores in the database.
"""

import sys
import logging
from full_compatibility_processor import run_full_compatibility_process, run_compatibility_for_sku

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('compatibility_runner')

def main():
    """Main function to run the compatibility processor"""
    if len(sys.argv) > 1:
        # Process a specific SKU
        sku = sys.argv[1]
        logger.info(f"Processing compatibility for single SKU: {sku}")
        run_compatibility_for_sku(sku)
    else:
        # Process all products
        logger.info("Processing compatibility for all products")
        run_full_compatibility_process()
    
    logger.info("Compatibility processing complete")

if __name__ == "__main__":
    main()