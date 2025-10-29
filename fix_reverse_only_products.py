#!/usr/bin/env python3
"""
Fix products that only have 'Reverse compatibility only' entries.
These products never had their forward compatibilities computed.
"""

import sys
from models import get_session, Product, ProductCompatibility
from sqlalchemy import func
from incremental_compute import compute_product_compatibilities, ProductIndex

def main():
    print("=" * 70)
    print("FIXING PRODUCTS WITH REVERSE-ONLY COMPATIBILITY")
    print("=" * 70)
    
    session = get_session()
    
    try:
        # Step 1: Find products with only reverse compatibility
        print("\n1. Finding products with incomplete compatibility data...")
        
        products_to_fix = []
        all_products = session.query(Product).all()
        
        for product in all_products:
            compats = session.query(ProductCompatibility).filter_by(base_product_id=product.id).all()
            
            # Check if this product only has reverse compatibility entries
            if len(compats) == 1:
                if compats[0].match_reason and 'Reverse compatibility only' in compats[0].match_reason:
                    products_to_fix.append(product)
            elif len(compats) == 0:
                products_to_fix.append(product)
        
        print(f"   Found {len(products_to_fix)} products with incomplete data")
        
        if not products_to_fix:
            print("\n✓ All products have complete compatibility data!")
            return
        
        # Show breakdown by category
        from collections import Counter
        category_counts = Counter([p.category for p in products_to_fix])
        print("\n   By category:")
        for cat, count in category_counts.most_common():
            print(f"     {cat}: {count}")
        
        # Step 2: Delete existing incomplete records
        print(f"\n2. Deleting incomplete compatibility records...")
        deleted = 0
        for product in products_to_fix:
            count = session.query(ProductCompatibility).filter_by(base_product_id=product.id).delete()
            deleted += count
        session.commit()
        print(f"   ✓ Deleted {deleted} incomplete records")
        
        # Step 3: Build product index
        print("\n3. Building product index...")
        index = ProductIndex(all_products)
        print(f"   ✓ Indexed {len(all_products)} products")
        
        # Step 4: Recompute compatibilities
        print(f"\n4. Computing compatibilities for {len(products_to_fix)} products...")
        batch_size = 50
        total_added = 0
        
        for i in range(0, len(products_to_fix), batch_size):
            batch = products_to_fix[i:i + batch_size]
            batch_records = []
            
            for product in batch:
                records = compute_product_compatibilities(product, index)
                batch_records.extend(records)
            
            # Deduplicate
            seen = set()
            unique_records = []
            for record in batch_records:
                key = (record['base_product_id'], record['compatible_product_id'])
                if key not in seen:
                    seen.add(key)
                    unique_records.append(record)
            
            # Insert
            if unique_records:
                session.bulk_insert_mappings(ProductCompatibility, unique_records)
                session.commit()
                total_added += len(unique_records)
            
            print(f"   Progress: {min(i + batch_size, len(products_to_fix))}/{len(products_to_fix)} products, {total_added:,} compatibilities added")
        
        print(f"\n   ✓ Added {total_added:,} compatibility records")
        
        # Step 5: Verify
        print("\n5. Verifying...")
        still_broken = []
        for product in products_to_fix:
            count = session.query(ProductCompatibility).filter_by(base_product_id=product.id).count()
            if count <= 1:
                still_broken.append(product.sku)
        
        if still_broken:
            print(f"   ⚠ {len(still_broken)} products still have issues:")
            for sku in still_broken[:10]:
                print(f"     - {sku}")
        else:
            print(f"   ✓ All {len(products_to_fix)} products now have compatibility data!")
        
        print("\n" + "=" * 70)
        print("✓ COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
