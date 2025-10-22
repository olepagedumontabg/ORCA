"""
Batch Compatibility Computation Script

This script computes compatibilities in batches to avoid timeouts.
It saves progress after each batch, so you can stop and resume anytime.

Usage:
  python3 batch_compute_compatibilities.py --batch-size 100
  python3 batch_compute_compatibilities.py --batch-size 50 --resume
"""

import os
import logging
import time
from datetime import datetime
from models import get_session, Product, ProductCompatibility
from logic import compatibility
import data_update_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_next_batch(batch_size=100, resume=False):
    """
    Get the next batch of products to process.
    
    Args:
        batch_size: Number of products per batch
        resume: If True, skip products that already have compatibilities
        
    Returns:
        list: Products to process
    """
    session = get_session()
    try:
        if resume:
            # Find products without compatibilities
            subquery = session.query(ProductCompatibility.base_product_id).distinct()
            query = session.query(Product).filter(~Product.id.in_(subquery))
        else:
            query = session.query(Product)
        
        products = query.limit(batch_size).all()
        return products
    finally:
        session.close()


def compute_batch(products):
    """
    Compute compatibilities for a batch of products.
    
    Args:
        products: List of Product objects
        
    Returns:
        tuple: (successful_count, compatibility_count, errors)
    """
    session = get_session()
    successful = 0
    compatibility_count = 0
    errors = []
    
    try:
        for idx, product in enumerate(products, 1):
            try:
                # Delete old compatibilities
                session.query(ProductCompatibility).filter_by(
                    base_product_id=product.id
                ).delete()
                
                # Compute new compatibilities
                results = compatibility.find_compatible_products(product.sku)
                
                if not results or not results.get('compatibles'):
                    successful += 1
                    continue
                
                # Store compatibilities (deduplicate by compatible_product_id)
                seen_compatible_ids = set()
                for category_data in results['compatibles']:
                    for compatible_product_data in category_data.get('products', []):
                        compatible_sku = compatible_product_data.get('sku', '').upper()
                        if not compatible_sku:
                            continue
                        
                        compatible_product = session.query(Product).filter_by(
                            sku=compatible_sku
                        ).first()
                        if not compatible_product:
                            continue
                        
                        # Skip if we've already added this compatibility
                        if compatible_product.id in seen_compatible_ids:
                            continue
                        seen_compatible_ids.add(compatible_product.id)
                        
                        compatibility_record = ProductCompatibility(
                            base_product_id=product.id,
                            compatible_product_id=compatible_product.id,
                            compatibility_score=100,
                            match_reason=f"Compatible {category_data.get('category', 'product')}",
                            incompatibility_reason=None
                        )
                        session.add(compatibility_record)
                        compatibility_count += 1
                
                successful += 1
                
                # Commit every 10 products
                if idx % 10 == 0:
                    session.commit()
                    logger.info(f"  Batch progress: {idx}/{len(products)} products, "
                              f"{compatibility_count} compatibilities so far")
                    
            except Exception as e:
                logger.error(f"Error processing {product.sku}: {str(e)}")
                errors.append((product.sku, str(e)))
                continue
        
        # Final commit
        session.commit()
        return (successful, compatibility_count, errors)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Batch processing error: {str(e)}")
        raise
    finally:
        session.close()


def get_stats():
    """Get current database statistics."""
    session = get_session()
    try:
        total_products = session.query(Product).count()
        total_compatibilities = session.query(ProductCompatibility).count()
        products_with_compatibilities = session.query(
            ProductCompatibility.base_product_id
        ).distinct().count()
        products_without_compatibilities = total_products - products_with_compatibilities
        
        return {
            'total_products': total_products,
            'total_compatibilities': total_compatibilities,
            'products_with_compatibilities': products_with_compatibilities,
            'products_without_compatibilities': products_without_compatibilities,
            'avg_compatibilities': total_compatibilities / products_with_compatibilities if products_with_compatibilities > 0 else 0
        }
    finally:
        session.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch compatibility computation')
    parser.add_argument('--batch-size', type=int, default=100, 
                       help='Number of products per batch (default: 100)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from where left off (skip products with compatibilities)')
    parser.add_argument('--max-batches', type=int, default=None,
                       help='Maximum number of batches to process (default: unlimited)')
    
    args = parser.parse_args()
    
    # Preload data into memory once
    logger.info("=" * 80)
    logger.info("BATCH COMPATIBILITY COMPUTATION")
    logger.info("=" * 80)
    logger.info(f"Batch size: {args.batch_size} products")
    logger.info(f"Resume mode: {args.resume}")
    logger.info(f"Max batches: {args.max_batches or 'unlimited'}")
    logger.info("")
    
    logger.info("Preloading product data into memory...")
    excel_path = os.path.join('data', 'Product Data.xlsx')
    if not data_update_service.load_data_into_memory(excel_path):
        logger.error("Failed to preload data")
        return
    logger.info("✓ Data preloaded successfully!")
    logger.info("")
    
    # Show initial stats
    logger.info("Initial Statistics:")
    stats = get_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("")
    
    # Process batches
    batch_num = 0
    total_processed = 0
    total_compatibilities = 0
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        # Check if we've hit max batches
        if args.max_batches and batch_num > args.max_batches:
            logger.info(f"Reached max batches limit ({args.max_batches})")
            break
        
        # Get next batch
        products = get_next_batch(args.batch_size, args.resume)
        if not products:
            logger.info("No more products to process!")
            break
        
        logger.info(f"Batch {batch_num}: Processing {len(products)} products...")
        batch_start = time.time()
        
        # Process batch
        try:
            successful, compat_count, errors = compute_batch(products)
            batch_time = time.time() - batch_start
            
            total_processed += successful
            total_compatibilities += compat_count
            
            logger.info(f"✓ Batch {batch_num} complete in {batch_time:.1f}s:")
            logger.info(f"  - Products processed: {successful}/{len(products)}")
            logger.info(f"  - Compatibilities added: {compat_count}")
            logger.info(f"  - Errors: {len(errors)}")
            if errors:
                for sku, error in errors[:3]:  # Show first 3 errors
                    logger.info(f"    • {sku}: {error}")
            logger.info("")
            
            # Show running totals
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            logger.info(f"Running Totals:")
            logger.info(f"  - Total products processed: {total_processed}")
            logger.info(f"  - Total compatibilities: {total_compatibilities}")
            logger.info(f"  - Processing rate: {rate:.1f} products/second")
            logger.info(f"  - Elapsed time: {elapsed/60:.1f} minutes")
            logger.info("")
            
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {str(e)}")
            break
    
    # Final stats
    logger.info("=" * 80)
    logger.info("FINAL STATISTICS")
    logger.info("=" * 80)
    final_stats = get_stats()
    for key, value in final_stats.items():
        logger.info(f"  {key}: {value}")
    logger.info("")
    logger.info(f"Total time: {(time.time() - start_time)/60:.1f} minutes")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
