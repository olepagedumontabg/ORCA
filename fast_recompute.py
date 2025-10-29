#!/usr/bin/env python3
"""
Fast recomputation - no logging, just process everything.
"""
import sys
import os
import time

# Disable all logging
import logging
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

from sqlalchemy.exc import IntegrityError
from models import get_session, Product, ProductCompatibility
import pandas as pd

def main():
    session = get_session()
    
    # Get status
    total_products = session.query(Product).count()
    products_with_compat = session.query(ProductCompatibility.base_product_id).distinct().count()
    remaining = total_products - products_with_compat
    
    print(f"Processing {remaining} remaining products out of {total_products} total...")
    
    if remaining == 0:
        print("Already complete!")
        session.close()
        return
    
    # Load Excel data
    data_file = '/home/runner/workspace/data/Product Data.xlsx'
    if not os.path.exists(data_file):
        data_file = 'data/Product Data.xlsx'
    
    # Get products without compatibilities
    products_to_process = session.query(Product).filter(
        ~Product.id.in_(
            session.query(ProductCompatibility.base_product_id).distinct()
        )
    ).all()
    
    # Build SKU to ID mapping
    all_products = session.query(Product.id, Product.sku).all()
    sku_to_id = {p.sku: p.id for p in all_products}
    
    start_time = time.time()
    total_new_compatibilities = 0
    compatibility_batch = []
    BATCH_SIZE = 1000
    
    for idx, product in enumerate(products_to_process, 1):
        try:
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
            
            # Bulk insert when batch is full
            if len(compatibility_batch) >= BATCH_SIZE:
                try:
                    session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                    session.commit()
                    total_new_compatibilities += len(compatibility_batch)
                    compatibility_batch = []
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
                    compatibility_batch = []
            
            # Progress indicator every 100 products
            if idx % 100 == 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed
                remaining_time = (len(products_to_process) - idx) / rate
                print(f"[{idx}/{len(products_to_process)}] {total_new_compatibilities:,} compatibilities | {rate:.1f}/sec | {remaining_time/60:.0f}min remaining", flush=True)
                    
        except:
            continue
    
    # Insert remaining
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
    
    # Final check
    products_with_compat_after = session.query(ProductCompatibility.base_product_id).distinct().count()
    total_compat_after = session.query(ProductCompatibility).count()
    
    print(f"\nCOMPLETE!")
    print(f"Processed: {len(products_to_process)} products")
    print(f"Compatibilities added: {total_new_compatibilities:,}")
    print(f"Total compatibilities in DB: {total_compat_after:,}")
    print(f"Products with compatibilities: {products_with_compat_after}/{total_products}")
    print(f"Time: {elapsed/60:.1f} minutes")
    
    # Clear API cache
    try:
        import app
        if hasattr(app, 'clear_api_cache'):
            app.clear_api_cache()
            print("API cache cleared")
    except:
        pass
    
    session.close()

if __name__ == "__main__":
    main()
