"""
Smart batch processor - only processes categories that should have compatibilities
"""
import os
import logging
from models import get_session, Product, ProductCompatibility
from logic import compatibility
import data_update_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Only these categories search for compatible products
TARGET_CATEGORIES = ['Shower Bases', 'Bathtubs', 'Showers', 'Tub Showers']

def get_unprocessed_products(batch_size=10):
    """Get products that need compatibility computation."""
    session = get_session()
    try:
        # Get products in target categories that don't have compatibilities yet
        subquery = session.query(ProductCompatibility.base_product_id).distinct()
        products = session.query(Product).filter(
            Product.category.in_(TARGET_CATEGORIES),
            ~Product.id.in_(subquery)
        ).limit(batch_size).all()
        return products
    finally:
        session.close()

def process_batch(products):
    """Process a batch of products."""
    session = get_session()
    compat_count = 0
    
    try:
        for product in products:
            # Delete old
            session.query(ProductCompatibility).filter_by(base_product_id=product.id).delete()
            
            # Compute new
            results = compatibility.find_compatible_products(product.sku)
            
            if not results or not results.get('compatibles'):
                continue
            
            # Store (with deduplication)
            seen_ids = set()
            for category_data in results['compatibles']:
                for compat_data in category_data.get('products', []):
                    compat_sku = compat_data.get('sku', '').upper()
                    if not compat_sku:
                        continue
                    
                    compat_product = session.query(Product).filter_by(sku=compat_sku).first()
                    if not compat_product or compat_product.id in seen_ids:
                        continue
                    
                    seen_ids.add(compat_product.id)
                    
                    session.add(ProductCompatibility(
                        base_product_id=product.id,
                        compatible_product_id=compat_product.id,
                        compatibility_score=100,
                        match_reason=f"Compatible {category_data.get('category', 'product')}",
                        incompatibility_reason=None
                    ))
                    compat_count += 1
            
            session.commit()
        
        return compat_count
    except Exception as e:
        session.rollback()
        logger.error(f"Error: {e}")
        return 0
    finally:
        session.close()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=10)
    parser.add_argument('--max-batches', type=int, default=1)
    args = parser.parse_args()
    
    # Preload data
    logger.info("Preloading data...")
    excel_path = os.path.join('data', 'Product Data.xlsx')
    data_update_service.load_data_into_memory(excel_path)
    
    total_compat = 0
    for batch_num in range(1, args.max_batches + 1):
        products = get_unprocessed_products(args.batch_size)
        if not products:
            logger.info("All products processed!")
            break
        
        logger.info(f"Batch {batch_num}: Processing {len(products)} products...")
        compat_count = process_batch(products)
        total_compat += compat_count
        logger.info(f"  Added {compat_count} compatibilities")
    
    logger.info(f"Total: {total_compat} compatibilities added")

if __name__ == '__main__':
    main()
