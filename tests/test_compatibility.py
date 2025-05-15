import os
import pandas as pd
import logging
from logic import bathtub_compatibility

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_test_data():
    """Load test data from the Excel file"""
    data = {}
    try:
        # Use the test data created by test_bathtubs.py
        excel_path = 'data/test/test_product_data.xlsx'
        
        if not os.path.exists(excel_path):
            logger.error(f"Test data file not found: {excel_path}")
            logger.info("Please run test_bathtubs.py first to generate test data")
            return {}
            
        excel = pd.ExcelFile(excel_path)
        
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            data[sheet_name] = df
            logger.debug(f"Loaded test sheet '{sheet_name}' with {len(df)} rows")
        
        return data
    except Exception as e:
        logger.error(f"Error loading test data: {str(e)}")
        return {}

def test_bathtub_compatibility():
    """Test the bathtub compatibility functionality"""
    # Load test data
    data = load_test_data()
    
    if not data or 'Bathtubs' not in data or 'Tub Doors' not in data or 'Walls' not in data:
        logger.error("Missing required test data!")
        return
    
    # Get the first test bathtub
    bathtub_info = data['Bathtubs'].iloc[0].to_dict()
    bathtub_id = bathtub_info.get('Unique ID')
    
    logger.info(f"Testing compatibility for bathtub: {bathtub_id} - {bathtub_info.get('Product Name')}")
    
    # Find compatible products
    compatible_products = bathtub_compatibility.find_bathtub_compatibilities(data, bathtub_info)
    
    # Display results
    logger.info(f"Found {len(compatible_products)} compatible categories")
    
    for category in compatible_products:
        logger.info(f"Category: {category['category']}")
        logger.info(f"Number of compatible products: {len(category['products'])}")
        
        for i, product in enumerate(category['products']):
            sku = product.get('sku', 'Unknown')
            name = product.get('name', 'Unnamed')
            logger.info(f"  {i+1}. {sku} - {name}")
    
    # Try with second test bathtub
    if len(data['Bathtubs']) > 1:
        bathtub_info = data['Bathtubs'].iloc[1].to_dict()
        bathtub_id = bathtub_info.get('Unique ID')
        
        logger.info(f"\nTesting compatibility for second bathtub: {bathtub_id} - {bathtub_info.get('Product Name')}")
        compatible_products = bathtub_compatibility.find_bathtub_compatibilities(data, bathtub_info)
        
        # Display results
        logger.info(f"Found {len(compatible_products)} compatible categories")
        
        for category in compatible_products:
            logger.info(f"Category: {category['category']}")
            logger.info(f"Number of compatible products: {len(category['products'])}")
            
            for i, product in enumerate(category['products']):
                sku = product.get('sku', 'Unknown')
                name = product.get('name', 'Unnamed')
                logger.info(f"  {i+1}. {sku} - {name}")
    
    logger.info("Compatibility test completed")

if __name__ == "__main__":
    test_bathtub_compatibility()