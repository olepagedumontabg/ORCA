#!/usr/bin/env python3
"""
Copy development database to production database.
Copies all products and compatibility records.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Product, ProductCompatibility, CompatibilityOverride
import time

def copy_database(dev_url, prod_url):
    """Copy all data from development to production database."""
    
    print("=" * 70)
    print("DATABASE COPY: Development → Production")
    print("=" * 70)
    print()
    
    # Create engines
    print("Connecting to databases...")
    dev_engine = create_engine(dev_url, pool_pre_ping=True)
    prod_engine = create_engine(prod_url, pool_pre_ping=True)
    
    DevSession = sessionmaker(bind=dev_engine)
    ProdSession = sessionmaker(bind=prod_engine)
    
    dev_session = DevSession()
    prod_session = ProdSession()
    
    try:
        # Step 1: Get counts from development
        print("\n1. Analyzing development database...")
        dev_products = dev_session.query(Product).count()
        dev_compatibilities = dev_session.query(ProductCompatibility).count()
        dev_overrides = dev_session.query(CompatibilityOverride).count()
        
        print(f"   Products: {dev_products:,}")
        print(f"   Compatibilities: {dev_compatibilities:,}")
        print(f"   Overrides: {dev_overrides:,}")
        
        # Step 2: Clear production tables
        print("\n2. Clearing production database...")
        prod_session.execute(text("TRUNCATE TABLE product_compatibility CASCADE"))
        prod_session.commit()
        # Skip compatibility_override if it doesn't exist
        try:
            prod_session.execute(text("TRUNCATE TABLE compatibility_override CASCADE"))
            prod_session.commit()
        except Exception:
            prod_session.rollback()  # Rollback failed transaction
        prod_session.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
        prod_session.commit()
        print("   ✓ Production tables cleared")
        
        # Step 3: Copy products
        print("\n3. Copying products...")
        start_time = time.time()
        
        # Fetch all products from dev
        dev_products_list = dev_session.query(Product).all()
        
        # Convert to dictionaries for bulk insert
        product_dicts = []
        for p in dev_products_list:
            product_dicts.append({
                'id': p.id,
                'sku': p.sku,
                'product_name': p.product_name,
                'brand': p.brand,
                'series': p.series,
                'family': p.family,
                'category': p.category,
                'length': p.length,
                'width': p.width,
                'height': p.height,
                'nominal_dimensions': p.nominal_dimensions,
                'attributes': p.attributes,
                'product_page_url': p.product_page_url,
                'image_url': p.image_url,
                'ranking': p.ranking,
                'created_at': p.created_at,
                'updated_at': p.updated_at
            })
        
        # Bulk insert products
        batch_size = 500
        for i in range(0, len(product_dicts), batch_size):
            batch = product_dicts[i:i + batch_size]
            prod_session.bulk_insert_mappings(Product, batch)
            prod_session.commit()
            print(f"   Progress: {min(i + batch_size, len(product_dicts)):,}/{len(product_dicts):,} products")
        
        elapsed = time.time() - start_time
        print(f"   ✓ Copied {len(product_dicts):,} products in {elapsed:.1f}s")
        
        # Step 4: Copy compatibilities
        print("\n4. Copying compatibilities...")
        start_time = time.time()
        
        # Fetch all compatibilities from dev
        dev_compat_list = dev_session.query(ProductCompatibility).all()
        
        # Convert to dictionaries for bulk insert
        compat_dicts = []
        for c in dev_compat_list:
            compat_dicts.append({
                'base_product_id': c.base_product_id,
                'compatible_product_id': c.compatible_product_id,
                'compatibility_score': c.compatibility_score,
                'match_reason': c.match_reason,
                'incompatibility_reason': c.incompatibility_reason,
                'computed_at': c.computed_at
            })
        
        # Bulk insert compatibilities
        for i in range(0, len(compat_dicts), batch_size):
            batch = compat_dicts[i:i + batch_size]
            prod_session.bulk_insert_mappings(ProductCompatibility, batch)
            prod_session.commit()
            print(f"   Progress: {min(i + batch_size, len(compat_dicts)):,}/{len(compat_dicts):,} compatibilities")
        
        elapsed = time.time() - start_time
        print(f"   ✓ Copied {len(compat_dicts):,} compatibilities in {elapsed:.1f}s")
        
        # Step 5: Copy overrides (if any)
        if dev_overrides > 0:
            print("\n5. Copying overrides...")
            start_time = time.time()
            
            try:
                dev_override_list = dev_session.query(CompatibilityOverride).all()
                override_dicts = []
                for o in dev_override_list:
                    override_dicts.append({
                        'base_sku': o.base_sku,
                        'compatible_sku': o.compatible_sku,
                        'override_type': o.override_type,
                        'reason': o.reason,
                        'created_at': o.created_at
                    })
                
                prod_session.bulk_insert_mappings(CompatibilityOverride, override_dicts)
                prod_session.commit()
                
                elapsed = time.time() - start_time
                print(f"   ✓ Copied {len(override_dicts):,} overrides in {elapsed:.1f}s")
            except Exception as e:
                print(f"   ⚠ Skipped overrides (table doesn't exist in production): {e}")
        
        # Step 6: Reset sequence for products table
        print("\n6. Resetting ID sequence...")
        max_id_result = prod_session.execute(text("SELECT MAX(id) FROM products")).fetchone()
        max_id = max_id_result[0] if max_id_result[0] else 0
        prod_session.execute(text(f"SELECT setval('products_id_seq', {max_id}, true)"))
        prod_session.commit()
        print(f"   ✓ Sequence reset to {max_id}")
        
        # Step 7: Analyze tables for optimal query performance
        print("\n7. Optimizing production database...")
        prod_session.execute(text("ANALYZE products"))
        prod_session.execute(text("ANALYZE product_compatibility"))
        prod_session.commit()
        print("   ✓ Tables analyzed")
        
        # Step 8: Verify
        print("\n8. Verifying production database...")
        prod_products = prod_session.query(Product).count()
        prod_compatibilities = prod_session.query(ProductCompatibility).count()
        try:
            prod_overrides = prod_session.query(CompatibilityOverride).count()
        except Exception:
            prod_overrides = 0
        
        print(f"   Products: {prod_products:,}")
        print(f"   Compatibilities: {prod_compatibilities:,}")
        print(f"   Overrides: {prod_overrides:,}")
        
        # Verify counts match
        if prod_products == dev_products and prod_compatibilities == dev_compatibilities:
            print("\n" + "=" * 70)
            print("✓ SUCCESS! Development database copied to production")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print("✗ ERROR! Counts don't match:")
            print(f"  Products: {dev_products} → {prod_products}")
            print(f"  Compatibilities: {dev_compatibilities} → {prod_compatibilities}")
            print("=" * 70)
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        prod_session.rollback()
        return False
    finally:
        dev_session.close()
        prod_session.close()


if __name__ == "__main__":
    # Get database URLs
    dev_url = os.environ.get("DATABASE_URL")
    prod_url = os.environ.get("PROD_DATABASE_URL")
    
    if not dev_url:
        print("Error: DATABASE_URL not set (development database)")
        sys.exit(1)
    
    if not prod_url:
        print("Error: PROD_DATABASE_URL not set (production database)")
        print("\nUsage: PROD_DATABASE_URL='your-prod-url' python copy_dev_to_prod.py")
        sys.exit(1)
    
    print(f"\nDevelopment: {dev_url[:50]}...")
    print(f"Production:  {prod_url[:50]}...")
    print()
    
    # Confirm
    response = input("Are you sure you want to copy development → production? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    
    # Execute copy
    success = copy_database(dev_url, prod_url)
    sys.exit(0 if success else 1)
