"""
Batch process bathtub compatibility computation.

This script processes bathtubs in batches to avoid Replit's 3-5 minute CPU limit.
Bathtubs find compatible: Tub Doors, Tub Screens, and Walls.
"""

import logging
import argparse
from models import get_session, Product, ProductCompatibility
from logic import compatibility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_bathtub_batch(start_idx: int, batch_size: int, preload_cache: bool = True):
    """
    Process a batch of bathtubs for compatibility computation.
    
    Args:
        start_idx: Starting index (0-based)
        batch_size: Number of bathtubs to process
        preload_cache: Whether to preload data into memory cache (default: True)
    
    Returns:
        dict: Statistics about processing
    """
    session = get_session()
    
    try:
        # Preload data into memory cache ONCE before processing
        if preload_cache:
            logger.info("Preloading data into memory cache...")
            compatibility.load_data()
            logger.info("Data preloaded successfully")
        
        # Get bathtubs that don't have compatibilities yet
        unprocessed_bathtubs = session.query(Product).filter(
            Product.category == 'Bathtubs',
            ~Product.id.in_(session.query(ProductCompatibility.base_product_id).distinct())
        ).offset(start_idx).limit(batch_size).all()
        
        if not unprocessed_bathtubs:
            logger.info("No unprocessed bathtubs found in this range")
            return {
                'processed': 0,
                'compatibilities_created': 0,
                'errors': 0
            }
        
        logger.info(f"Processing {len(unprocessed_bathtubs)} bathtubs starting from index {start_idx}")
        
        stats = {
            'processed': 0,
            'compatibilities_created': 0,
            'errors': 0
        }
        
        for idx, product in enumerate(unprocessed_bathtubs, 1):
            try:
                logger.info(f"[{idx}/{len(unprocessed_bathtubs)}] Processing {product.sku}: {product.product_name}")
                
                # Compute compatibilities using Excel-based logic
                results = compatibility.find_compatible_products(product.sku)
                
                if not results or not results.get('compatibles'):
                    logger.info(f"  No compatibles found for {product.sku}")
                    stats['processed'] += 1
                    continue
                
                # Store compatibilities (forward direction only, we'll create reverse later)
                seen_ids = set()
                compat_count = 0
                
                for category_data in results['compatibles']:
                    category = category_data.get('category', 'Unknown')
                    products = category_data.get('products', [])
                    
                    for compatible_product_data in products:
                        compatible_sku = compatible_product_data.get('sku', '').upper()
                        if not compatible_sku:
                            continue
                        
                        compatible_product = session.query(Product).filter_by(sku=compatible_sku).first()
                        if not compatible_product or compatible_product.id in seen_ids:
                            continue
                        
                        seen_ids.add(compatible_product.id)
                        
                        # Create compatibility record
                        compatibility_record = ProductCompatibility(
                            base_product_id=product.id,
                            compatible_product_id=compatible_product.id,
                            compatibility_score=100,
                            match_reason=f"Compatible {category}",
                            incompatibility_reason=None
                        )
                        session.add(compatibility_record)
                        compat_count += 1
                
                session.commit()
                stats['compatibilities_created'] += compat_count
                stats['processed'] += 1
                
                logger.info(f"  ✓ Created {compat_count} compatibility records")
                
            except Exception as e:
                logger.error(f"  ✗ Error processing {product.sku}: {str(e)}")
                stats['errors'] += 1
                session.rollback()
                continue
        
        logger.info("="*80)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info(f"Bathtubs processed: {stats['processed']}")
        logger.info(f"Compatibilities created: {stats['compatibilities_created']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("="*80)
        
        return stats
        
    finally:
        session.close()


def get_batch_info():
    """Get information about batching requirements."""
    session = get_session()
    try:
        total_bathtubs = session.query(Product).filter_by(category='Bathtubs').count()
        processed = session.query(Product).filter(
            Product.category == 'Bathtubs',
            Product.id.in_(session.query(ProductCompatibility.base_product_id).distinct())
        ).count()
        remaining = total_bathtubs - processed
        
        print("="*80)
        print("BATHTUB COMPATIBILITY PROCESSING STATUS")
        print("="*80)
        print(f"Total bathtubs: {total_bathtubs}")
        print(f"Processed: {processed}")
        print(f"Remaining: {remaining}")
        print("="*80)
        print(f"\nRecommended batch size: 50 bathtubs")
        print(f"Number of batches needed: {(remaining + 49) // 50}")
        print("="*80)
        
    finally:
        session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch process bathtub compatibilities')
    parser.add_argument('--start', type=int, default=0, help='Starting index (default: 0)')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size (default: 50)')
    parser.add_argument('--info', action='store_true', help='Show batch processing info')
    
    args = parser.parse_args()
    
    if args.info:
        get_batch_info()
    else:
        process_bathtub_batch(args.start, args.batch_size)
