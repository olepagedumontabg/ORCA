#!/usr/bin/env python3
"""
Continuous recomputation - processes products one at a time with immediate saves.
Run this and let it work - progress is saved after each product.
"""
import sys
import os

# Disable logging
import logging
logging.disable(logging.CRITICAL)

from sqlalchemy.exc import IntegrityError
from models import get_session, Product, ProductCompatibility

print("Starting continuous recomputation...", flush=True)

session = get_session()

# Build SKU to ID mapping once
all_products = session.query(Product.id, Product.sku).all()
sku_to_id = {p.sku: p.id for p in all_products}
total_products = len(all_products)

processed_count = 0
total_compat_added = 0

while True:
    # Get next product without compatibilities
    product = session.query(Product).filter(
        ~Product.id.in_(
            session.query(ProductCompatibility.base_product_id).distinct()
        )
    ).first()
    
    if not product:
        # All done!
        final_count = session.query(ProductCompatibility.base_product_id).distinct().count()
        final_total = session.query(ProductCompatibility).count()
        print(f"\n✓ COMPLETE! {final_count}/{total_products} products with {final_total:,} compatibilities")
        
        # Clear API cache
        try:
            import app
            if hasattr(app, 'clear_api_cache'):
                app.clear_api_cache()
                print("✓ API cache cleared")
        except:
            pass
        
        break
    
    try:
        # Find compatibilities for this product
        from logic.compatibility import find_compatible_products
        result = find_compatible_products(product.sku)
        
        compat_count = 0
        
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
                        
                        # Forward compatibility
                        try:
                            c1 = ProductCompatibility(
                                base_product_id=product.id,
                                compatible_product_id=comp_product_id,
                                compatibility_score=comp_item.get('compatibility_score', 100),
                                match_reason=comp_item.get('match_reason', ''),
                                incompatibility_reason=comp_item.get('incompatibility_reason', '') or None
                            )
                            session.add(c1)
                            session.flush()
                            compat_count += 1
                        except IntegrityError:
                            session.rollback()
                        
                        # Reverse compatibility
                        try:
                            c2 = ProductCompatibility(
                                base_product_id=comp_product_id,
                                compatible_product_id=product.id,
                                compatibility_score=comp_item.get('compatibility_score', 100),
                                match_reason=comp_item.get('match_reason', ''),
                                incompatibility_reason=comp_item.get('incompatibility_reason', '') or None
                            )
                            session.add(c2)
                            session.flush()
                            compat_count += 1
                        except IntegrityError:
                            session.rollback()
        
        # Commit after each product
        session.commit()
        processed_count += 1
        total_compat_added += compat_count
        
        if processed_count % 10 == 0:
            remaining = total_products - session.query(ProductCompatibility.base_product_id).distinct().count()
            print(f"[{processed_count}] {product.sku}: +{compat_count} | Total: {total_compat_added:,} | Remaining: {remaining}", flush=True)
            
    except Exception as e:
        # Skip this product on error
        session.rollback()
        # Mark it as processed with a dummy entry so we don't loop forever
        try:
            dummy = ProductCompatibility(
                base_product_id=product.id,
                compatible_product_id=product.id,
                compatibility_score=0,
                match_reason='Error during processing',
                incompatibility_reason='Processing error'
            )
            session.add(dummy)
            session.commit()
        except:
            session.rollback()
        processed_count += 1

session.close()
