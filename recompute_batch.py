#!/usr/bin/env python3
"""
Batch recomputation script - processes products in manageable chunks.
Run this script multiple times until all products are processed.
"""

import logging
import time
from sqlalchemy.exc import IntegrityError
from models import get_session, Product, ProductCompatibility
import pandas as pd
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Batch size - how many products to process per run
BATCH_SIZE = 100

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
        except:
            pass
    
    return data

def main():
    session = get_session()
    
    try:
        # Get total status
        total_products = session.query(Product).count()
        products_with_compat = session.query(ProductCompatibility.base_product_id).distinct().count()
        remaining = total_products - products_with_compat
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH RECOMPUTATION STATUS")
        logger.info(f"{'='*60}")
        logger.info(f"Total products: {total_products}")
        logger.info(f"Completed: {products_with_compat} ({products_with_compat/total_products*100:.1f}%)")
        logger.info(f"Remaining: {remaining}")
        logger.info(f"{'='*60}\n")
        
        if remaining == 0:
            logger.info("✓ ALL PRODUCTS PROCESSED! Database is 100% complete.\n")
            
            # Clear API cache
            try:
                import app
                if hasattr(app, 'clear_api_cache'):
                    app.clear_api_cache()
                    logger.info("✓ API cache cleared\n")
            except:
                pass
            
            return
        
        # Load Excel data once
        excel_data = load_excel_data()
        
        # Get products without compatibilities (limit to batch size)
        products_to_process = session.query(Product).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).distinct()
            )
        ).limit(BATCH_SIZE).all()
        
        batch_count = len(products_to_process)
        logger.info(f"Processing batch of {batch_count} products...\n")
        
        start_time = time.time()
        processed = 0
        total_new_compatibilities = 0
        
        # Build SKU to ID mapping
        all_products = session.query(Product.id, Product.sku).all()
        sku_to_id = {p.sku: p.id for p in all_products}
        
        compatibility_batch = []
        INSERT_BATCH_SIZE = 500
        
        for idx, product in enumerate(products_to_process, 1):
            try:
                # Import here to use cached data
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
                            
                            for single_sku in [s.strip() for s in comp_sku.split('|')]:
                                comp_product_id = sku_to_id.get(single_sku)
                                if not comp_product_id:
                                    continue
                                
                                compatibility_batch.append({
                                    'base_product_id': product.id,
                                    'compatible_product_id': comp_product_id,
                                    'compatibility_score': comp_item.get('compatibility_score', 100),
                                    'match_reason': comp_item.get('match_reason', ''),
                                    'incompatibility_reason': comp_item.get('incompatibility_reason', '') or None
                                })
                                
                                compatibility_batch.append({
                                    'base_product_id': comp_product_id,
                                    'compatible_product_id': product.id,
                                    'compatibility_score': comp_item.get('compatibility_score', 100),
                                    'match_reason': comp_item.get('match_reason', ''),
                                    'incompatibility_reason': comp_item.get('incompatibility_reason', '') or None
                                })
                
                # Insert batch if full
                if len(compatibility_batch) >= INSERT_BATCH_SIZE:
                    try:
                        session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                        session.commit()
                        total_new_compatibilities += len(compatibility_batch)
                        compatibility_batch = []
                    except IntegrityError:
                        session.rollback()
                        # Fall back to individual inserts
                        for compat_dict in compatibility_batch:
                            try:
                                exists = session.query(ProductCompatibility).filter_by(
                                    base_product_id=compat_dict['base_product_id'],
                                    compatible_product_id=compat_dict['compatible_product_id']
                                ).first()
                                if not exists:
                                    session.add(ProductCompatibility(**compat_dict))
                                    session.commit()
                                    total_new_compatibilities += 1
                            except IntegrityError:
                                session.rollback()
                        compatibility_batch = []
                
                processed += 1
                
                if processed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    logger.info(f"  [{processed}/{batch_count}] {total_new_compatibilities:,} compatibilities | {rate:.1f}/sec")
                        
            except Exception as e:
                logger.error(f"Error processing {product.sku}: {str(e)}")
                continue
        
        # Insert any remaining
        if compatibility_batch:
            try:
                session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                session.commit()
                total_new_compatibilities += len(compatibility_batch)
            except IntegrityError:
                session.rollback()
                for compat_dict in compatibility_batch:
                    try:
                        exists = session.query(ProductCompatibility).filter_by(
                            base_product_id=compat_dict['base_product_id'],
                            compatible_product_id=compat_dict['compatible_product_id']
                        ).first()
                        if not exists:
                            session.add(ProductCompatibility(**compat_dict))
                            session.commit()
                            total_new_compatibilities += 1
                    except IntegrityError:
                        session.rollback()
        
        elapsed = time.time() - start_time
        
        # Final status
        products_with_compat_after = session.query(ProductCompatibility.base_product_id).distinct().count()
        remaining_after = total_products - products_with_compat_after
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ BATCH COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Processed: {processed} products")
        logger.info(f"Compatibilities added: {total_new_compatibilities:,}")
        logger.info(f"Time: {elapsed:.1f} seconds")
        logger.info(f"Rate: {processed/elapsed:.1f} products/sec")
        logger.info(f"{'='*60}")
        logger.info(f"OVERALL PROGRESS: {products_with_compat_after}/{total_products} ({products_with_compat_after/total_products*100:.1f}%)")
        logger.info(f"Remaining: {remaining_after} products")
        logger.info(f"{'='*60}\n")
        
        if remaining_after > 0:
            logger.info(f"⏩ Run this script again to process the next batch\n")
        else:
            logger.info(f"✓ ALL DONE! Database is 100% complete.\n")
            
            # Clear API cache when fully complete
            try:
                import app
                if hasattr(app, 'clear_api_cache'):
                    app.clear_api_cache()
                    logger.info("✓ API cache cleared\n")
            except:
                pass
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
