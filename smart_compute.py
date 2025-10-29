#!/usr/bin/env python3
"""
Smart compatibility computation - handles connections properly, processes in batches.
"""
import sys
import os
import time

# Disable logging
import logging
logging.disable(logging.CRITICAL)

from sqlalchemy.exc import IntegrityError, OperationalError
from models import get_session, Product, ProductCompatibility
from logic.compatibility import load_data
from logic import base_compatibility, bathtub_compatibility, shower_compatibility, tubshower_compatibility

# Process in chunks to avoid connection timeouts
CHUNK_SIZE = 50

def extract_sku(prod):
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
    try:
        if category == 'Shower Bases':
            return base_compatibility.find_base_compatibilities(data, product_info)
        elif category == 'Bathtubs':
            return bathtub_compatibility.find_bathtub_compatibilities(data, product_info)
        elif category == 'Showers':
            return shower_compatibility.find_shower_compatibilities(data, product_info)
        elif category == 'Tub Showers':
            return tubshower_compatibility.find_tubshower_compatibilities(data, product_info)
    except:
        pass
    return []

print("Smart computation starting...")
print("Loading data...", flush=True)

# Load data once
data = load_data()
if not data:
    print("ERROR: No data available")
    sys.exit(1)

print("Data loaded", flush=True)

# Track progress
total_processed = 0
total_compat_added = 0
start_time = time.time()

while True:
    # Get a fresh session for each chunk
    session = get_session()
    
    try:
        # Check status
        total_products = session.query(Product).count()
        products_with_compat = session.query(ProductCompatibility.base_product_id).distinct().count()
        remaining = total_products - products_with_compat
        
        if remaining == 0:
            print(f"\n✓ COMPLETE! All {total_products} products processed")
            session.close()
            break
        
        # Get next chunk of products
        products_to_process = session.query(Product).filter(
            ~Product.id.in_(
                session.query(ProductCompatibility.base_product_id).distinct()
            )
        ).limit(CHUNK_SIZE).all()
        
        if not products_to_process:
            print("No more products to process")
            session.close()
            break
        
        # Build SKU mapping for this session
        all_products = session.query(Product.id, Product.sku, Product.category).all()
        sku_to_id = {p.sku: p.id for p in all_products}
        
        chunk_compat = 0
        compatibility_batch = []
        
        for product in products_to_process:
            try:
                # Find product info
                product_category = product.category
                product_info = None
                
                if product_category in data:
                    df = data[product_category]
                    if 'Unique ID' in df.columns:
                        product_row = df[df['Unique ID'].astype(str).str.upper() == product.sku.upper()]
                        if not product_row.empty:
                            product_info = product_row.iloc[0].to_dict()
                
                if not product_info:
                    continue
                
                # Find compatibilities
                compatible_products = find_compatibilities_bulk(data, product_info, product_category)
                
                if not compatible_products:
                    continue
                
                # Extract compatibility records
                for category_group in compatible_products:
                    if 'products' not in category_group:
                        continue
                    
                    for comp_item in category_group['products']:
                        comp_sku = extract_sku(comp_item)
                        if not comp_sku:
                            continue
                        
                        for single_sku in [s.strip() for s in comp_sku.split('|')]:
                            comp_product_id = sku_to_id.get(single_sku)
                            if not comp_product_id:
                                continue
                            
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
            except:
                continue
        
        # Bulk insert all compatibilities for this chunk
        if compatibility_batch:
            try:
                session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                session.commit()
                chunk_compat = len(compatibility_batch)
            except IntegrityError:
                session.rollback()
                # Slower path for duplicates
                for compat_dict in compatibility_batch:
                    try:
                        exists = session.query(ProductCompatibility).filter_by(
                            base_product_id=compat_dict['base_product_id'],
                            compatible_product_id=compat_dict['compatible_product_id']
                        ).first()
                        if not exists:
                            session.add(ProductCompatibility(**compat_dict))
                            session.commit()
                            chunk_compat += 1
                    except IntegrityError:
                        session.rollback()
        
        total_processed += len(products_to_process)
        total_compat_added += chunk_compat
        
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        
        # Get updated status
        new_count = session.query(ProductCompatibility.base_product_id).distinct().count()
        new_remaining = total_products - new_count
        eta = (new_remaining / rate / 60) if rate > 0 else 0
        
        print(f"[{new_count}/{total_products}] +{chunk_compat} compatibilities | {rate:.1f}/sec | {new_remaining} remaining | ETA: {eta:.0f}min", flush=True)
        
    except OperationalError as e:
        print(f"Connection error, retrying... ({str(e)[:50]})")
        session.rollback()
        time.sleep(2)
        continue
    except Exception as e:
        print(f"Error: {str(e)[:100]}")
        session.rollback()
    finally:
        session.close()
    
    # Small delay between chunks
    time.sleep(0.1)

# Final summary
elapsed = time.time() - start_time
print(f"\nProcessed: {total_processed} products")
print(f"Compatibilities: {total_compat_added:,}")
print(f"Time: {elapsed/60:.1f} minutes")
print(f"Rate: {total_processed/elapsed:.1f} products/sec")

# Clear API cache
try:
    import app
    if hasattr(app, 'clear_api_cache'):
        app.clear_api_cache()
        print("API cache cleared")
except:
    pass
