"""
Process compatibility for a single SKU.
This script is used to quickly process compatibility for a specific SKU
without having to process all products.
"""
import sys
import logging
from full_compatibility_processor import run_compatibility_for_sku

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('run_single_sku')

def main():
    """Main function to process compatibility for a single SKU"""
    if len(sys.argv) < 2:
        logger.error("Please provide a SKU to process")
        print("Usage: python run_single_sku.py <SKU>")
        sys.exit(1)
    
    sku = sys.argv[1].strip().upper()
    logger.info(f"Processing compatibility for SKU: {sku}")
    
    # Call compatibility processor for single SKU
    run_compatibility_for_sku(sku)
    
    logger.info(f"Finished processing compatibility for SKU: {sku}")
    logger.info("You can now query the compatibility information using: python get_compatibility.py " + sku)

if __name__ == "__main__":
    main()