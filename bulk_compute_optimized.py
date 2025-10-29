#!/usr/bin/env python3
"""
Optimized bulk compatibility computation.
Loads data ONCE and processes all products in batch.
"""
import sys
import os
import time

# Disable all logging for maximum speed
import logging
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

from sqlalchemy.exc import IntegrityError
from models import get_session, Product, ProductCompatibility
from logic.compatibility import load_data
from logic import base_compatibility, bathtub_compatibility, shower_compatibility, tubshower_compatibility
import pandas as pd
import numpy as np

def extract_sku(prod):
    """Extract SKU from product dict"""
    if not isinstance(prod, dict):
        return str(prod).strip()
    for k in ("sku", "SKU", "Unique ID", "unique_id"):
        if k in prod and prod[k]:
            return str(prod[k]).strip()
    if prod.get("is_combo"):
        main = str(prod.get("main_product", {}).get("sku", "")).strip()
        sec = str(prod.get("secondary_product", {}).get("sku", "")).strip()
        return f"{main}|{sec}".strip("|")
    return ""

def find_compatibilities_bulk(data, product_info, category):
    """Find compatibilities for a product using preloaded data"""
    try:
        if category == 'Shower Bases':
            return base_compatibility.find_base_compatibilities(data, product_info)
        elif category == 'Bathtubs':
            return bathtub_compatibility.find_bathtub_compatibilities(data, product_info)
        elif category == 'Showers':
            return shower_compatibility.find_shower_compatibilities(data, product_info)
        elif category == 'Tub Showers':
            return tubshower_compatibility.find_tubshower_compatibilities(data, product_info)
        else:
            return []
    except:
        return []

def main():
    print("Starting optimized bulk computation...")
    print("Loading data once for all products...", flush=True)
    
    # Load data ONCE
    data = load_data()
    if not data:
        print("ERROR: No data available")
        return
    
    print("Data loaded successfully", flush=True)
    
    session = get_session()
    
    # Get all products that need processing
    total_products = session.query(Product).count()
    products_with_compat = session.query(ProductCompatibility.base_product_id).distinct().count()
    
    products_to_process = session.query(Product).filter(
        ~Product.id.in_(
            session.query(ProductCompatibility.base_product_id).distinct()
        )
    ).all()
    
    total = len(products_to_process)
    print(f"\nProcessing {total} products (already completed: {products_with_compat}/{total_products})")
    
    if total == 0:
        print("All products already processed!")
        session.close()
        return
    
    # Build SKU to ID mapping
    all_products = session.query(Product.id, Product.sku, Product.category).all()
    sku_to_id = {p.sku: p.id for p in all_products}
    sku_to_category = {p.sku: p.category for p in all_products}
    
    print(f"Built mapping for {len(sku_to_id)} products\n", flush=True)
    
    start_time = time.time()
    processed = 0
    total_compatibilities = 0
    compatibility_batch = []
    BATCH_SIZE = 1000
    
    for product in products_to_process:
        try:
            # Find product info in the loaded data
            product_category = product.category
            product_info = None
            
            # Get the DataFrame for this category
            if product_category in data:
                df = data[product_category]
                if 'Unique ID' in df.columns:
                    product_row = df[df['Unique ID'].astype(str).str.upper() == product.sku.upper()]
                    if not product_row.empty:
                        product_info = product_row.iloc[0].to_dict()
            
            if not product_info:
                processed += 1
                continue
            
            # Find compatibilities using the cached data
            compatible_products = find_compatibilities_bulk(data, product_info, product_category)
            
            if not compatible_products:
                processed += 1
                continue
            
            # Process each compatible product
            for category_group in compatible_products:
                if 'products' not in category_group:
                    continue
                    
                products_in_group = category_group['products']
                
                for comp_item in products_in_group:
                    comp_sku = extract_sku(comp_item)
                    if not comp_sku:
                        continue
                    
                    # Handle compound SKUs
                    for single_sku in [s.strip() for s in comp_sku.split('|')]:
                        comp_product_id = sku_to_id.get(single_sku)
                        if not comp_product_id:
                            continue
                        
                        # Add both forward and reverse compatibility
                        compatibility_batch.extend([
                            {
                                'base_product_id': product.id,
                                'compatible_product_id': comp_product_id,
                                'compatibility_score': comp_item.get('compatibility_score', 100),
                                'match_reason': comp_item.get('match_reason', ''),
                                'incompatibility_reason': None
                            },
                            {
                                'base_product_id': comp_product_id,
                                'compatible_product_id': product.id,
                                'compatibility_score': comp_item.get('compatibility_score', 100),
                                'match_reason': comp_item.get('match_reason', ''),
                                'incompatibility_reason': None
                            }
                        ])
            
            # Bulk insert when batch is full
            if len(compatibility_batch) >= BATCH_SIZE:
                try:
                    session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                    session.commit()
                    total_compatibilities += len(compatibility_batch)
                    compatibility_batch = []
                except IntegrityError:
                    session.rollback()
                    # Slow path for duplicates
                    for compat_dict in compatibility_batch:
                        try:
                            exists = session.query(ProductCompatibility).filter_by(
                                base_product_id=compat_dict['base_product_id'],
                                compatible_product_id=compat_dict['compatible_product_id']
                            ).first()
                            if not exists:
                                session.add(ProductCompatibility(**compat_dict))
                                session.commit()
                                total_compatibilities += 1
                        except IntegrityError:
                            session.rollback()
                    compatibility_batch = []
            
            processed += 1
            
            # Progress updates
            if processed % 50 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = total - processed
                eta_minutes = (remaining / rate / 60) if rate > 0 else 0
                print(f"[{processed}/{total}] {total_compatibilities:,} compatibilities | {rate:.1f}/sec | ETA: {eta_minutes:.0f}min", flush=True)
        
        except Exception as e:
            processed += 1
            continue
    
    # Insert remaining batch
    if compatibility_batch:
        try:
            session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
            session.commit()
            total_compatibilities += len(compatibility_batch)
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
                        total_compatibilities += 1
                except IntegrityError:
                    session.rollback()
    
    elapsed = time.time() - start_time
    
    # Final status
    final_count = session.query(ProductCompatibility.base_product_id).distinct().count()
    final_total = session.query(ProductCompatibility).count()
    
    print(f"\n{'='*60}")
    print(f"COMPLETE!")
    print(f"{'='*60}")
    print(f"Products processed: {processed:,}")
    print(f"Compatibilities added: {total_compatibilities:,}")
    print(f"Total in database: {final_total:,}")
    print(f"Coverage: {final_count}/{total_products} ({final_count/total_products*100:.1f}%)")
    print(f"Time: {elapsed/60:.1f} minutes ({processed/elapsed:.1f} products/sec)")
    print(f"{'='*60}")
    
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
