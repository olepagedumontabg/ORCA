#!/usr/bin/env python3
"""
Add New Products and Compute Compatibilities
Complete workflow for adding products from Excel to database
"""

import sys
import time
from models import get_session, Product, ProductCompatibility
from db_sync_service import sync_database_from_excel
from incremental_compute import compute_incremental


def add_products_from_excel(excel_path: str = 'data/Product Data.xlsx', 
                            auto_compute: bool = True,
                            verbose: bool = True):
    """
    Add new products from Excel and optionally compute compatibilities
    
    Args:
        excel_path: Path to Excel file
        auto_compute: Automatically compute compatibilities for new products
        verbose: Print progress updates
    
    Returns:
        (products_added, compatibilities_computed)
    """
    if verbose:
        print("=" * 70)
        print("ADD PRODUCTS FROM EXCEL")
        print("=" * 70)
        print()
    
    # Step 1: Sync database with Excel
    if verbose:
        print("Step 1: Syncing database with Excel...")
        print(f"  Source: {excel_path}")
        print()
    
    start_time = time.time()
    
    try:
        added, updated, deleted = sync_database_from_excel(excel_path)
        
        sync_time = time.time() - start_time
        
        if verbose:
            print()
            print(f"✓ Database sync complete ({sync_time:.1f}s)")
            print(f"  Added: {added} products")
            print(f"  Updated: {updated} products")
            print(f"  Deleted: {deleted} products")
            print()
        
        # Step 2: Compute compatibilities for new products
        products_processed = 0
        compatibilities_added = 0
        
        if auto_compute and added > 0:
            if verbose:
                print("Step 2: Computing compatibilities for new products...")
                print()
            
            compute_start = time.time()
            products_processed, compatibilities_added = compute_incremental(
                batch_size=50,
                verbose=verbose
            )
            compute_time = time.time() - compute_start
            
            if verbose:
                print()
                print(f"✓ Compatibility computation complete ({compute_time:.1f}s)")
                print(f"  Processed: {products_processed} products")
                print(f"  Added: {compatibilities_added:,} compatibilities")
        
        # Final summary
        total_time = time.time() - start_time
        
        if verbose:
            print()
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"  Products Added: {added}")
            print(f"  Products Updated: {updated}")
            print(f"  Compatibilities Computed: {compatibilities_added:,}")
            print(f"  Total Time: {total_time/60:.1f} minutes")
            print()
        
        return added, compatibilities_added
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


def show_status():
    """Show current database status"""
    session = get_session()
    
    total_products = session.query(Product).count()
    processed_products = session.query(ProductCompatibility.base_product_id).distinct().count()
    total_compatibilities = session.query(ProductCompatibility).count()
    new_products = session.query(Product).filter(
        ~Product.id.in_(
            session.query(ProductCompatibility.base_product_id).distinct()
        )
    ).count()
    
    session.close()
    
    print("=" * 70)
    print("DATABASE STATUS")
    print("=" * 70)
    print(f"  Total Products: {total_products:,}")
    print(f"  Processed Products: {processed_products:,}")
    print(f"  New Products (no compatibilities): {new_products:,}")
    print(f"  Total Compatibility Records: {total_compatibilities:,}")
    print(f"  Bidirectional Matches: ~{total_compatibilities // 2:,}")
    print()
    
    if new_products > 0:
        print(f"⚠ {new_products} products need compatibility computation")
        print("  Run: python add_products.py")
    else:
        print("✓ All products have compatibility data")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'status':
            show_status()
            return
        elif sys.argv[1] == 'help':
            print("Usage:")
            print("  python add_products.py              - Add products and compute compatibilities")
            print("  python add_products.py status       - Show database status")
            print("  python add_products.py help         - Show this help")
            return
    
    # Default: add products and compute compatibilities
    add_products_from_excel(
        excel_path='data/Product Data.xlsx',
        auto_compute=True,
        verbose=True
    )


if __name__ == '__main__':
    main()
