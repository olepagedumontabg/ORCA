#!/usr/bin/env python3
"""
Process ALL products through compatibility scripts.
Direct approach using existing compatibility functions.
"""

import logging
import time
from models import get_session, Product, ProductCompatibility
from logic.compatibility import find_compatible_products

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    session = get_session()
    
    try:
        # Get products without compatibilities
        products_to_process = session.query(Product).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).distinct()
            )
        ).all()
        
        total = len(products_to_process)
        
        if total == 0:
            logger.info("✓ All products already have compatibilities in the database!")
            return
        
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING {total:,} PRODUCTS")
        logger.info(f"{'='*70}\n")
        
        start_time = time.time()
        processed = 0
        total_new_compatibilities = 0
        
        for idx, product in enumerate(products_to_process, 1):
            product_compatibilities = 0
            
            try:
                # Use the existing compatibility script
                result = find_compatible_products(product.sku)
                
                if result and isinstance(result, dict):
                    compatibles_list = result.get('compatibles', [])
                    
                    for category_group in compatibles_list:
                        products_in_group = category_group.get('products', [])
                        
                        for comp_item in products_in_group:
                            comp_sku = comp_item.get('sku')
                            if not comp_sku:
                                continue
                            
                            # Handle compound SKUs (split by |)
                            for single_sku in [s.strip() for s in comp_sku.split('|')]:
                                # Find in database
                                comp_product = session.query(Product).filter_by(sku=single_sku).first()
                                if not comp_product:
                                    continue
                                
                                # Check if already exists
                                try:
                                    exists = session.query(ProductCompatibility).filter_by(
                                        base_product_id=product.id,
                                        compatible_product_id=comp_product.id
                                    ).first()
                                    
                                    if not exists:
                                        # Create forward relationship
                                        new_comp = ProductCompatibility(
                                            base_product_id=product.id,
                                            compatible_product_id=comp_product.id,
                                            compatibility_score=comp_item.get('compatibility_score', 100),
                                            match_reason=comp_item.get('match_reason', ''),
                                            incompatibility_reason=comp_item.get('incompatibility_reason', '')
                                        )
                                        session.add(new_comp)
                                        session.flush()
                                        product_compatibilities += 1
                                        total_new_compatibilities += 1
                                except Exception:
                                    session.rollback()
                                
                                # Create reverse relationship
                                try:
                                    reverse_exists = session.query(ProductCompatibility).filter_by(
                                        base_product_id=comp_product.id,
                                        compatible_product_id=product.id
                                    ).first()
                                    
                                    if not reverse_exists:
                                        reverse_comp = ProductCompatibility(
                                            base_product_id=comp_product.id,
                                            compatible_product_id=product.id,
                                            compatibility_score=comp_item.get('compatibility_score', 100),
                                            match_reason=comp_item.get('match_reason', ''),
                                            incompatibility_reason=comp_item.get('incompatibility_reason', '')
                                        )
                                        session.add(reverse_comp)
                                        session.flush()
                                        product_compatibilities += 1
                                        total_new_compatibilities += 1
                                except Exception:
                                    session.rollback()
                
                # Commit after each product
                session.commit()
                processed += 1
                
                # Progress report every 10 products
                if idx % 10 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = total - processed
                    est_time_left = remaining / rate if rate > 0 else 0
                    logger.info(
                        f"[{idx:,}/{total:,}] {processed:,} products done | "
                        f"{total_new_compatibilities:,} compatibilities | "
                        f"{rate:.1f}/sec | ~{est_time_left/60:.0f}min left"
                    )
                    
            except Exception as e:
                logger.error(f"Error on {product.sku}: {e}")
                session.rollback()
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}")
        logger.info(f"✓ PROCESSING COMPLETE!")
        logger.info(f"  Products processed: {processed:,}")
        logger.info(f"  Compatibilities created: {total_new_compatibilities:,}")
        logger.info(f"  Total time: {elapsed/60:.1f} minutes")
        logger.info(f"  Average rate: {processed/elapsed:.1f} products/second")
        logger.info(f"{'='*70}\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
