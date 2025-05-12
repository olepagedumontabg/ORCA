"""
Get compatibility information for a specific SKU from the database.
This script is used to retrieve compatibility information that has been generated
by the compatibility processor and stored in the database.
"""
import os
import sys
import logging
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('get_compatibility')

# Get database URL from environment variable
DB_URL = os.environ.get('DATABASE_URL')

if not DB_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

def get_sku_compatibility(sku):
    """
    Get compatibility information for a specific SKU from the database
    
    Args:
        sku (str): The SKU to query for
        
    Returns:
        dict: Dictionary containing the product information and compatible products
    """
    engine = create_engine(DB_URL)
    
    try:
        # First, check if the product exists
        with engine.connect() as conn:
            product_query = text("""
                SELECT sku, category, brand, family, series, nominal_dimensions, installation, 
                       max_door_width, width, length, height
                FROM products
                WHERE sku = :sku
            """)
            product_result = conn.execute(product_query, {"sku": sku}).fetchone()
            
            if not product_result:
                logger.error(f"Product not found for SKU: {sku}")
                return {"success": False, "message": f"Product not found for SKU: {sku}"}
            
            # Get product details
            product = {
                "sku": product_result[0],
                "category": product_result[1],
                "brand": product_result[2],
                "family": product_result[3],
                "series": product_result[4],
                "nominal_dimensions": product_result[5],
                "installation": product_result[6],
                "max_door_width": product_result[7],
                "width": product_result[8],
                "length": product_result[9],
                "height": product_result[10]
            }
            
            # Get compatibility information
            compat_query = text("""
                SELECT c.target_sku, c.target_category, c.requires_return_panel,
                       p.brand, p.family, p.series, p.nominal_dimensions
                FROM compatibilities c
                JOIN products p ON c.target_sku = p.sku
                WHERE c.source_sku = :sku
                ORDER BY c.target_category, c.target_sku
            """)
            compat_results = conn.execute(compat_query, {"sku": sku}).fetchall()
            
            # Organize results by category
            compatibilities = {}
            for row in compat_results:
                category = row[1]
                if category not in compatibilities:
                    compatibilities[category] = []
                
                compat_item = {
                    "sku": row[0],
                    "requires_return": bool(row[2]),
                    "return_panel": row[2] if row[2] else None,
                    "brand": row[3],
                    "family": row[4],
                    "series": row[5],
                    "nominal_dimensions": row[6]
                }
                compatibilities[category].append(compat_item)
            
            return {
                "success": True,
                "product": product,
                "compatibilities": compatibilities
            }
    
    except Exception as e:
        logger.error(f"Error getting compatibility for SKU {sku}: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def main():
    """Main function to query compatibility information"""
    if len(sys.argv) < 2:
        logger.error("Please provide a SKU to query")
        print("Usage: python get_compatibility.py <SKU>")
        sys.exit(1)
    
    sku = sys.argv[1].strip().upper()
    logger.info(f"Getting compatibility information for SKU: {sku}")
    
    result = get_sku_compatibility(sku)
    
    if result["success"]:
        print(f"Product: {result['product']['sku']} - {result['product']['brand']} {result['product']['family']}")
        print(f"Category: {result['product']['category']}")
        print(f"Nominal Dimensions: {result['product']['nominal_dimensions']}")
        print(f"Installation: {result['product']['installation']}")
        print("\nCompatible Products:")
        
        for category, items in result["compatibilities"].items():
            print(f"\n{category} ({len(items)}):")
            for i, item in enumerate(items, 1):
                return_info = f" (Requires return panel: {item['return_panel']})" if item['requires_return'] else ""
                print(f"  {i}. {item['sku']} - {item['brand']} {item['family']} {item['nominal_dimensions']}{return_info}")
    else:
        print(f"Error: {result['message']}")

if __name__ == "__main__":
    main()