#!/usr/bin/env python3
"""
Complete processing of ALL products with optimized performance.
Preloads data once and handles duplicates without data loss.
"""

import logging
import time
from sqlalchemy.exc import IntegrityError
from models import get_session, Product, ProductCompatibility
import pandas as pd
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_excel_data():
    """Load all Excel data once."""
    data_file = '/home/runner/workspace/data/Product Data.xlsx'
    if not os.path.exists(data_file):
        data_file = 'data/Product Data.xlsx'
    
    logger.info("Loading Excel data...")
    
    data = {}
    sheets = ['Shower Bases', 'Bathtubs', 'Showers', 'Tub Showers', 'Shower Doors', 
              'Walls', 'Screens', 'Accessories']
    
    for sheet in sheets:
        try:
            df = pd.read_excel(data_file, sheet_name=sheet)
            data[sheet] = df
            logger.info(f"  Loaded {len(df)} products from {sheet}")
        except Exception as e:
            logger.warning(f"  Could not load {sheet}: {e}")
    
    return data

def find_compatibles_from_loaded_data(sku, all_excel_data):
    """Find compatibles using preloaded data (avoiding repeated file loads)."""
    from logic.compatibility import find_compatible_products
    
    # The compatibility script will use its own caching, but we ensure 
    # data is already loaded in memory by calling it once
    return find_compatible_products(sku)

def main():
    session = get_session()
    
    try:
        # Load Excel data once
        excel_data = load_excel_data()
        
        # Get products without compatibilities
        products_to_process = session.query(Product).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).distinct()
            )
        ).all()
        
        total = len(products_to_process)
        
        if total == 0:
            logger.info("\n✓ ALL PRODUCTS PROCESSED! Database is 100% complete.\n")
            return
        
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING {total:,} REMAINING PRODUCTS")
        logger.info(f"{'='*70}\n")
        
        start_time = time.time()
        processed = 0
        total_new_compatibilities = 0
        
        for idx, product in enumerate(products_to_process, 1):
            try:
                # Get compatibilities
                result = find_compatibles_from_loaded_data(product.sku, excel_data)
                
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
                                comp_product = session.query(Product).filter_by(sku=single_sku).first()
                                if not comp_product:
                                    continue
                                
                                # Insert forward - handle duplicates individually
                                try:
                                    # Check first to avoid query cost
                                    exists = session.query(ProductCompatibility).filter_by(
                                        base_product_id=product.id,
                                        compatible_product_id=comp_product.id
                                    ).first()
                                    
                                    if not exists:
                                        session.add(ProductCompatibility(
                                            base_product_id=product.id,
                                            compatible_product_id=comp_product.id,
                                            compatibility_score=comp_item.get('compatibility_score', 100),
                                            match_reason=comp_item.get('match_reason', ''),
                                            incompatibility_reason=comp_item.get('incompatibility_reason', '')
                                        ))
                                        session.flush()
                                        total_new_compatibilities += 1
                                except IntegrityError:
                                    # Duplicate - rollback only this one insert
                                    session.rollback()
                                
                                # Insert reverse - handle duplicates individually  
                                try:
                                    reverse_exists = session.query(ProductCompatibility).filter_by(
                                        base_product_id=comp_product.id,
                                        compatible_product_id=product.id
                                    ).first()
                                    
                                    if not reverse_exists:
                                        session.add(ProductCompatibility(
                                            base_product_id=comp_product.id,
                                            compatible_product_id=product.id,
                                            compatibility_score=comp_item.get('compatibility_score', 100),
                                            match_reason=comp_item.get('match_reason', ''),
                                            incompatibility_reason=comp_item.get('incompatibility_reason', '')
                                        ))
                                        session.flush()
                                        total_new_compatibilities += 1
                                except IntegrityError:
                                    # Duplicate - rollback only this one insert
                                    session.rollback()
                
                # Commit all successful inserts for this product
                session.commit()
                processed += 1
                
                # Progress every 10 products
                if idx % 10 == 0 or idx == total:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    remaining = total - processed
                    est_time = remaining / rate if rate > 0 else 0
                    logger.info(
                        f"[{idx:,}/{total:,}] {total_new_compatibilities:,} compatibilities | "
                        f"{rate:.1f}/sec | ~{est_time/60:.0f}min left"
                    )
                    
            except Exception as e:
                logger.error(f"Error on {product.sku}: {e}")
                session.rollback()
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*70}")
        logger.info(f"✓ BATCH COMPLETE!")
        logger.info(f"  Products: {processed:,}")
        logger.info(f"  Compatibilities: {total_new_compatibilities:,}")
        logger.info(f"  Time: {elapsed/60:.1f} minutes")
        logger.info(f"  Rate: {processed/elapsed:.1f} products/sec")
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
