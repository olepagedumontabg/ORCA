#!/usr/bin/env python3
"""
Process ALL products through compatibility scripts and update database.
This script processes every product regardless of current compatibility status.
"""

import logging
import time
from models import get_session, Product, ProductCompatibility
from logic.compatibility import get_compatible_products
from data_loader import load_all_data

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def process_all_products():
    """Process all products through compatibility scripts."""
    session = get_session()
    
    try:
        # Load Excel data
        logger.info("Loading product data from Excel...")
        all_data = load_all_data()
        
        # Get all products that need processing (no compatibilities)
        products_without_comp = session.query(Product).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).distinct()
            )
        ).all()
        
        total = len(products_without_comp)
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING {total:,} PRODUCTS WITHOUT COMPATIBILITIES")
        logger.info(f"{'='*70}\n")
        
        if total == 0:
            logger.info("✓ All products already have compatibilities!")
            return
        
        start_time = time.time()
        processed = 0
        total_compatibilities = 0
        
        for idx, product in enumerate(products_without_comp, 1):
            try:
                # Get compatibilities from the compatibility script
                result = get_compatible_products(product.sku, all_data)
                
                if result and isinstance(result, dict):
                    compatibles = result.get('compatibles', [])
                    
                    # Process each compatible category
                    for category_data in compatibles:
                        products_list = category_data.get('products', [])
                        
                        for comp_product in products_list:
                            comp_sku = comp_product.get('sku')
                            if not comp_sku:
                                continue
                            
                            # Handle compound SKUs (e.g., "SKU1|SKU2")
                            comp_skus = [s.strip() for s in comp_sku.split('|')]
                            
                            for single_sku in comp_skus:
                                # Find the compatible product in database
                                comp_db_product = session.query(Product).filter_by(sku=single_sku).first()
                                if not comp_db_product:
                                    continue
                                
                                # Create forward compatibility
                                existing = session.query(ProductCompatibility).filter_by(
                                    base_product_id=product.id,
                                    compatible_product_id=comp_db_product.id
                                ).first()
                                
                                if not existing:
                                    forward_comp = ProductCompatibility(
                                        base_product_id=product.id,
                                        compatible_product_id=comp_db_product.id,
                                        compatibility_score=comp_product.get('compatibility_score', 100),
                                        match_reason=comp_product.get('match_reason', ''),
                                        incompatibility_reason=comp_product.get('incompatibility_reason', '')
                                    )
                                    session.add(forward_comp)
                                    total_compatibilities += 1
                                
                                # Create reverse compatibility
                                reverse_existing = session.query(ProductCompatibility).filter_by(
                                    base_product_id=comp_db_product.id,
                                    compatible_product_id=product.id
                                ).first()
                                
                                if not reverse_existing:
                                    reverse_comp = ProductCompatibility(
                                        base_product_id=comp_db_product.id,
                                        compatible_product_id=product.id,
                                        compatibility_score=comp_product.get('compatibility_score', 100),
                                        match_reason=comp_product.get('match_reason', ''),
                                        incompatibility_reason=comp_product.get('incompatibility_reason', '')
                                    )
                                    session.add(reverse_comp)
                                    total_compatibilities += 1
                
                session.commit()
                processed += 1
                
                # Show progress every 10 products
                if idx % 10 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {idx:,}/{total:,} products | {total_compatibilities:,} compatibilities | {rate:.1f} products/sec")
                
            except Exception as e:
                logger.error(f"Error processing {product.sku}: {e}")
                session.rollback()
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}")
        logger.info(f"✓ COMPLETE!")
        logger.info(f"  Processed: {processed:,} products")
        logger.info(f"  Created: {total_compatibilities:,} compatibility relationships")
        logger.info(f"  Time: {elapsed/60:.1f} minutes")
        logger.info(f"  Rate: {processed/elapsed:.1f} products/sec")
        logger.info(f"{'='*70}\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    process_all_products()
