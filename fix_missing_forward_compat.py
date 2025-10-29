#!/usr/bin/env python3
"""
Fix products that should have forward compatibility but don't.
Specifically targets Shower Bases, Bathtubs, Showers, and Tub Showers.
"""

import logging
import time
from models import get_session, Product, ProductCompatibility

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    session = get_session()
    
    try:
        # Categories that SHOULD have forward compatibility
        base_categories = ['Shower Bases', 'Bathtubs', 'Showers', 'Tub Showers']
        
        # Find products in these categories WITHOUT forward compatibility
        products_to_fix = session.query(Product).filter(
            Product.category.in_(base_categories)
        ).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).filter(
                    ProductCompatibility.compatibility_score > 0
                ).distinct()
            )
        ).all()
        
        total_to_fix = len(products_to_fix)
        
        if total_to_fix == 0:
            logger.info("✓ All base products have forward compatibility!")
            return
        
        logger.info(f"\n{'='*70}")
        logger.info(f"FIXING PRODUCTS WITH MISSING FORWARD COMPATIBILITY")
        logger.info(f"{'='*70}")
        logger.info(f"Total products to fix: {total_to_fix}")
        
        # Group by category
        by_category = {}
        for p in products_to_fix:
            if p.category not in by_category:
                by_category[p.category] = []
            by_category[p.category].append(p)
        
        for cat, prods in by_category.items():
            logger.info(f"  {cat}: {len(prods)} products")
        
        logger.info(f"{'='*70}\n")
        
        # Build SKU to ID mapping for fast lookups
        all_products = session.query(Product.id, Product.sku).all()
        sku_to_id = {p.sku: p.id for p in all_products}
        
        # Process each product
        start_time = time.time()
        processed = 0
        total_new_compatibilities = 0
        compatibility_batch = []
        BATCH_SIZE = 100  # Reduced to avoid SQL parameter limit
        
        for idx, product in enumerate(products_to_fix, 1):
            try:
                # Delete existing compatibility records for this product first
                session.query(ProductCompatibility).filter(
                    ProductCompatibility.base_product_id == product.id
                ).delete(synchronize_session=False)
                session.commit()  # Commit the delete before inserting new records
                
                # Compute compatibilities
                from logic.compatibility import find_compatible_products
                result = find_compatible_products(product.sku)
                
                if result and isinstance(result, dict):
                    compatibles_list = result.get('compatibles', [])
                    
                    for category_group in compatibles_list:
                        products_in_group = category_group.get('products', [])
                        
                        for comp_item in products_in_group:
                            comp_sku = comp_item.get('sku')
                            if not comp_sku:
                                continue
                            
                            # Handle compound SKUs
                            for single_sku in [s.strip() for s in comp_sku.split('|')]:
                                comp_product_id = sku_to_id.get(single_sku)
                                if not comp_product_id:
                                    continue
                                
                                compatibility_batch.append(ProductCompatibility(
                                    base_product_id=product.id,
                                    compatible_product_id=comp_product_id,
                                    compatibility_score=comp_item.get('compatibility_score', 100),
                                    match_reason=comp_item.get('match_reason', ''),
                                    incompatibility_reason=None
                                ))
                
                processed += 1
                
                # Batch insert
                if len(compatibility_batch) >= BATCH_SIZE:
                    session.bulk_save_objects(compatibility_batch)
                    session.commit()
                    total_new_compatibilities += len(compatibility_batch)
                    compatibility_batch = []
                
                # Progress update
                if idx % 10 == 0 or idx == total_to_fix:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    eta = (total_to_fix - processed) / rate if rate > 0 else 0
                    
                    logger.info(f"Progress: {processed}/{total_to_fix} products ({processed/total_to_fix*100:.1f}%) "
                              f"- {total_new_compatibilities:,} compatibilities added "
                              f"- {rate:.1f} products/sec - ETA: {eta:.0f}s")
            
            except Exception as e:
                logger.warning(f"Error processing {product.sku}: {str(e)}")
                continue
        
        # Insert remaining batch
        if compatibility_batch:
            session.bulk_save_objects(compatibility_batch)
            session.commit()
            total_new_compatibilities += len(compatibility_batch)
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        logger.info(f"COMPLETED")
        logger.info(f"{'='*70}")
        logger.info(f"Products processed: {processed:,}")
        logger.info(f"New compatibility records: {total_new_compatibilities:,}")
        logger.info(f"Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        logger.info(f"{'='*70}\n")
        
        # Clear API cache
        try:
            import app
            if hasattr(app, 'clear_api_cache'):
                app.clear_api_cache()
                logger.info("✓ API cache cleared\n")
        except:
            pass
        
    finally:
        session.close()

if __name__ == '__main__':
    main()
