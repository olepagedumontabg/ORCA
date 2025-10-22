"""
Background Compatibility Processing Script

This script processes remaining products in small batches and can be stopped/restarted.
It saves progress automatically and can run continuously in the background.

Usage:
  python3 process_remaining_compatibilities.py
"""

import os
import logging
import time
from datetime import datetime
from models import get_session, Product, ProductCompatibility
from logic import compatibility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 10  # Small batches to avoid timeout
SLEEP_BETWEEN_BATCHES = 0.5  # Short pause between batches


def get_products_without_compatibilities(limit=None):
    """Get products that don't have any compatibilities yet"""
    session = get_session()
    try:
        subquery = session.query(ProductCompatibility.base_product_id).distinct()
        query = session.query(Product).filter(~Product.id.in_(subquery))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    finally:
        session.close()


def process_single_product(product):
    """Process a single product and return compatibility count"""
    session = get_session()
    compatibilities_added = 0
    
    try:
        # Check if already has compatibilities
        existing = session.query(ProductCompatibility).filter_by(
            base_product_id=product.id
        ).count()
        
        if existing > 0:
            return 0
        
        # Compute compatibilities using Excel logic
        results = compatibility.find_compatible_products(product.sku)
        
        if not results or not results.get('compatibles'):
            return 0
        
        # Store forward compatibilities
        seen_compatible_ids = set()
        for category_data in results['compatibles']:
            for compatible_product_data in category_data.get('products', []):
                compatible_sku = compatible_product_data.get('sku', '').upper()
                if not compatible_sku:
                    continue
                
                # Handle compound SKUs (e.g., "138996|138998")
                individual_skus = [s.strip() for s in compatible_sku.split('|')]
                
                for individual_sku in individual_skus:
                    compatible_product = session.query(Product).filter_by(
                        sku=individual_sku
                    ).first()
                    if not compatible_product:
                        continue
                    
                    if compatible_product.id in seen_compatible_ids:
                        continue
                    seen_compatible_ids.add(compatible_product.id)
                    
                    # Forward compatibility
                    forward = ProductCompatibility(
                        base_product_id=product.id,
                        compatible_product_id=compatible_product.id,
                        compatibility_score=100,
                        match_reason=f"Compatible {category_data.get('category', 'product')}",
                        incompatibility_reason=None
                    )
                    session.add(forward)
                    compatibilities_added += 1
                    
                    # Reverse compatibility (bidirectional)
                    existing_reverse = session.query(ProductCompatibility).filter_by(
                        base_product_id=compatible_product.id,
                        compatible_product_id=product.id
                    ).first()
                    
                    if not existing_reverse:
                        reverse = ProductCompatibility(
                            base_product_id=compatible_product.id,
                            compatible_product_id=product.id,
                            compatibility_score=100,
                            match_reason=f"Compatible {category_data.get('category', 'product')}",
                            incompatibility_reason=None
                        )
                        session.add(reverse)
                        compatibilities_added += 1
        
        session.commit()
        return compatibilities_added
        
    except Exception as e:
        logger.error(f"Error processing {product.sku}: {str(e)}")
        session.rollback()
        return 0
    finally:
        session.close()


def main():
    """Main processing loop"""
    start_time = time.time()
    total_processed = 0
    total_compatibilities = 0
    
    logger.info("=" * 70)
    logger.info("BACKGROUND COMPATIBILITY PROCESSING")
    logger.info("=" * 70)
    
    while True:
        # Get next batch
        products = get_products_without_compatibilities(limit=BATCH_SIZE)
        
        if not products:
            logger.info("\n" + "=" * 70)
            logger.info("ALL PRODUCTS PROCESSED!")
            logger.info(f"Total processed: {total_processed:,} products")
            logger.info(f"Total compatibilities: {total_compatibilities:,}")
            elapsed = time.time() - start_time
            logger.info(f"Total time: {elapsed/60:.1f} minutes")
            logger.info("=" * 70)
            break
        
        # Process batch
        batch_start = time.time()
        batch_compatibilities = 0
        
        for product in products:
            comp_count = process_single_product(product)
            batch_compatibilities += comp_count
            total_compatibilities += comp_count
            total_processed += 1
            
            if total_processed % 10 == 0:
                elapsed = time.time() - start_time
                rate = total_processed / elapsed if elapsed > 0 else 0
                logger.info(f"Progress: {total_processed:,} products, "
                          f"{total_compatibilities:,} compatibilities, "
                          f"{rate:.1f} products/sec")
        
        # Short pause between batches
        time.sleep(SLEEP_BETWEEN_BATCHES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
