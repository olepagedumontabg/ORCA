#!/usr/bin/env python3
"""
Fix compatibility for a single product SKU.
This re-computes and saves all compatibilities for one product.

Usage: python fix_single_product.py SKU
Example: python fix_single_product.py 410000-501-001
"""

import sys
import os
from logic import compatibility
from models import get_session, Product, ProductCompatibility
from sqlalchemy import delete

def fix_product_compatibility(sku):
    """Re-compute and save compatibility for a single SKU."""
    print(f"Processing SKU: {sku}")
    
    # Get compatibility from logic
    results = compatibility.find_compatible_products(sku)
    
    if not results or not results.get('product'):
        print(f"ERROR: Product {sku} not found in Excel data")
        return False
    
    print(f"Product: {results['product'].get('Product Name')}")
    
    # Count expected compatibilities
    total_expected = 0
    for cat in results.get('compatibles', []):
        products = cat.get('products', [])
        if products:
            total_expected += len(products)
            print(f"  {cat['category']}: {len(products)} products")
    
    if total_expected == 0:
        print("No compatibilities found in Excel. Skipping.")
        return False
    
    print(f"\nTotal expected: {total_expected} compatibilities")
    
    # Save to database
    session = get_session()
    
    try:
        # Get base product
        base_product = session.query(Product).filter_by(sku=sku.upper()).first()
        if not base_product:
            print(f"ERROR: Product {sku} not found in database")
            session.close()
            return False
        
        print(f"Found product in database (ID: {base_product.id})")
        
        # Delete existing compatibilities for this product
        deleted = session.query(ProductCompatibility).filter_by(
            base_product_id=base_product.id
        ).delete()
        print(f"Deleted {deleted} existing compatibility records")
        session.commit()
        
        # Add new compatibilities
        added = 0
        for cat_data in results.get('compatibles', []):
            category = cat_data.get('category')
            products = cat_data.get('products', [])
            
            for comp_product_data in products:
                comp_sku = comp_product_data.get('sku')
                if not comp_sku:
                    continue
                
                comp_product = session.query(Product).filter_by(sku=comp_sku.upper()).first()
                if not comp_product:
                    print(f"  WARNING: Compatible product {comp_sku} not found in database")
                    continue
                
                # Create compatibility record
                compat = ProductCompatibility(
                    base_product_id=base_product.id,
                    compatible_product_id=comp_product.id,
                    compatibility_score=100,
                    match_reason='',
                    incompatibility_reason=''
                )
                session.add(compat)
                added += 1
        
        session.commit()
        print(f"\n✅ Added {added} compatibility records")
        
        # Verify
        final_count = session.query(ProductCompatibility).filter_by(
            base_product_id=base_product.id
        ).count()
        print(f"✅ Final count in database: {final_count}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        session.close()
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    sku = sys.argv[1]
    success = fix_product_compatibility(sku)
    
    if success:
        print("\n✅ Done! Product compatibility fixed.")
        sys.exit(0)
    else:
        print("\n❌ Failed to fix product compatibility.")
        sys.exit(1)
