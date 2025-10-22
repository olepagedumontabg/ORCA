"""
Batch process ALL remaining products that don't have compatibilities yet.

This script processes products in batches to avoid Replit's CPU timeout.
Focuses on: Shower Bases, Bathtubs, Showers, and Tub Showers.
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


def get_unprocessed_stats():
    """Get statistics on unprocessed products by category."""
    session = get_session()
    try:
        categories = ['Shower Bases', 'Bathtubs', 'Showers', 'Tub Showers']
        stats = {}
        
        for category in categories:
            total = session.query(Product).filter_by(category=category).count()
            processed = session.query(Product).filter(
                Product.category == category,
                Product.id.in_(session.query(ProductCompatibility.base_product_id).distinct())
            ).count()
            stats[category] = {
                'total': total,
                'processed': processed,
                'remaining': total - processed
            }
        
        return stats
    finally:
        session.close()


def process_batch(category: str, start_idx: int, batch_size: int, preload_cache: bool = True):
    """
    Process a batch of products for compatibility computation.
    
    Args:
        category: Product category to process
        start_idx: Starting index (0-based)
        batch_size: Number of products to process
        preload_cache: Whether to preload data into memory cache
    
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
        
        # Get unprocessed products
        unprocessed = session.query(Product).filter(
            Product.category == category,
            ~Product.id.in_(session.query(ProductCompatibility.base_product_id).distinct())
        ).offset(start_idx).limit(batch_size).all()
        
        if not unprocessed:
            logger.info(f"No unprocessed {category} found in this range")
            return {'processed': 0, 'compatibilities_created': 0, 'errors': 0}
        
        logger.info(f"Processing {len(unprocessed)} {category} starting from index {start_idx}")
        
        stats = {'processed': 0, 'compatibilities_created': 0, 'errors': 0}
        
        for idx, product in enumerate(unprocessed, 1):
            try:
                logger.info(f"[{idx}/{len(unprocessed)}] Processing {product.sku}: {product.product_name}")
                
                # Compute compatibilities using Excel-based logic
                results = compatibility.find_compatible_products(product.sku)
                
                if not results or not results.get('compatibles'):
                    logger.info(f"  No compatibles found for {product.sku}")
                    stats['processed'] += 1
                    continue
                
                # Store compatibilities (forward direction only)
                seen_ids = set()
                compat_count = 0
                
                # Use no_autoflush to prevent premature flushes during queries
                with session.no_autoflush:
                    for category_data in results['compatibles']:
                        for compatible_product_data in category_data.get('products', []):
                            compatible_sku = compatible_product_data.get('sku', '').upper()
                            if not compatible_sku:
                                continue
                            
                            compatible_product = session.query(Product).filter_by(sku=compatible_sku).first()
                            if not compatible_product or compatible_product.id in seen_ids:
                                continue
                            
                            seen_ids.add(compatible_product.id)
                            
                            # Check if compatibility already exists
                            existing = session.query(ProductCompatibility).filter_by(
                                base_product_id=product.id,
                                compatible_product_id=compatible_product.id
                            ).first()
                            
                            if existing:
                                continue
                            
                            # Create compatibility record
                            compatibility_record = ProductCompatibility(
                                base_product_id=product.id,
                                compatible_product_id=compatible_product.id,
                                compatibility_score=100,
                                match_reason=f"Compatible {category_data.get('category')}",
                                incompatibility_reason=None
                            )
                            session.add(compatibility_record)
                            compat_count += 1
                
                # Commit after each product to isolate errors
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
        logger.info(f"Products processed: {stats['processed']}")
        logger.info(f"Compatibilities created: {stats['compatibilities_created']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("="*80)
        
        return stats
        
    finally:
        session.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch process product compatibilities')
    parser.add_argument('--category', type=str, default='Shower Bases',
                       choices=['Shower Bases', 'Bathtubs', 'Showers', 'Tub Showers'],
                       help='Product category to process')
    parser.add_argument('--start', type=int, default=0, help='Starting index (default: 0)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size (default: 20)')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_unprocessed_stats()
        print("="*80)
        print("UNPROCESSED PRODUCTS STATISTICS")
        print("="*80)
        for category, data in stats.items():
            print(f"\n{category}:")
            print(f"  Total: {data['total']}")
            print(f"  Processed: {data['processed']}")
            print(f"  Remaining: {data['remaining']}")
            if data['remaining'] > 0:
                batches = (data['remaining'] + 19) // 20  # Assuming batch size of 20
                print(f"  Batches needed (size 20): {batches}")
        print("="*80)
    else:
        process_batch(args.category, args.start, args.batch_size)
