"""
Database Sync Service for Bathroom Compatibility Finder

This service integrates with the existing FTP data update service to:
1. Update the database when new Excel files are downloaded
2. Recompute compatibilities for changed products
3. Maintain sync between Excel files and database

Usage:
  - Called automatically by data_update_service.py after successful FTP download
  - Can be run manually: python3 db_sync_service.py --sync
"""

import os
import logging
import pandas as pd
from datetime import datetime
from typing import Set, List, Tuple

logger = logging.getLogger(__name__)

# Import database components
try:
    from models import get_session, Product, ProductCompatibility
    from logic import compatibility
    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database modules not available")
    DB_AVAILABLE = False


def sync_database_from_excel(excel_path: str = None) -> dict:
    """
    Synchronize database with Excel file data.
    
    Args:
        excel_path: Path to Excel file (defaults to data/Product Data.xlsx)
        
    Returns:
        dict: {
            'products_added': int,
            'products_updated': int,
            'products_deleted': int,
            'added_products': list of {sku, name, category},
            'updated_products': list of {sku, name, category, changes},
            'deleted_products': list of {sku, name, category}
        }
    """
    if not DB_AVAILABLE:
        logger.error("Database not available for sync")
        return {'products_added': 0, 'products_updated': 0, 'products_deleted': 0, 
                'added_products': [], 'updated_products': [], 'deleted_products': []}
    
    if excel_path is None:
        excel_path = os.path.join('data', 'Product Data.xlsx')
    
    logger.info(f"Starting database sync from {excel_path}")
    
    session = get_session()
    added = 0
    updated = 0
    deleted = 0
    
    # Track detailed changes
    added_products = []
    updated_products = []
    deleted_products = []
    
    try:
        # Load Excel data
        data = {}
        xls = pd.ExcelFile(excel_path)
        for sheet_name in xls.sheet_names:
            data[sheet_name] = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # Get all existing SKUs from database
        existing_skus = {p.sku for p in session.query(Product.sku).all()}
        excel_skus = set()
        
        # Process each category
        for category, df in data.items():
            if 'Unique ID' not in df.columns:
                logger.warning(f"Skipping category '{category}' - no 'Unique ID' column")
                continue
            
            logger.info(f"Syncing category: {category} ({len(df)} products)")
            
            for _, row in df.iterrows():
                sku = str(row.get('Unique ID', '')).strip().upper()
                if not sku or sku == 'NAN':
                    continue
                
                excel_skus.add(sku)
                
                # Prepare product data
                product_data = {
                    'sku': sku,
                    'product_name': str(row.get('Product Name', '')) if pd.notna(row.get('Product Name')) else None,
                    'brand': str(row.get('Brand', '')) if pd.notna(row.get('Brand')) else None,
                    'series': str(row.get('Series', '')) if pd.notna(row.get('Series')) else None,
                    'family': str(row.get('Family', '')) if pd.notna(row.get('Family')) else None,
                    'category': category,
                    'length': float(row.get('Length')) if pd.notna(row.get('Length')) else None,
                    'width': float(row.get('Width')) if pd.notna(row.get('Width')) else None,
                    'height': float(row.get('Height')) if pd.notna(row.get('Height')) else None,
                    'nominal_dimensions': str(row.get('Nominal Dimensions', '')) if pd.notna(row.get('Nominal Dimensions')) else None,
                    'product_page_url': str(row.get('Product Page URL', '')) if pd.notna(row.get('Product Page URL')) else None,
                    'image_url': str(row.get('Image URL', '')) if pd.notna(row.get('Image URL')) else None,
                    'ranking': int(row.get('Ranking')) if pd.notna(row.get('Ranking')) else None,
                }
                
                # Build attributes JSON
                attributes = {}
                exclude_columns = ['Unique ID', 'Product Name', 'Brand', 'Series', 'Family', 
                                 'Length', 'Width', 'Height', 'Nominal Dimensions', 
                                 'Product Page URL', 'Image URL', 'Ranking']
                
                for col in df.columns:
                    if col not in exclude_columns and pd.notna(row.get(col)):
                        value = row.get(col)
                        if isinstance(value, (int, float, str, bool)):
                            attributes[col] = value
                        else:
                            attributes[col] = str(value)
                
                product_data['attributes'] = attributes
                
                # Check if product exists
                existing_product = session.query(Product).filter_by(sku=sku).first()
                
                if existing_product:
                    # Update existing product and track changes
                    changed = False
                    changes = {}
                    for key, value in product_data.items():
                        if key != 'created_at':
                            old_value = getattr(existing_product, key)
                            if old_value != value:
                                setattr(existing_product, key, value)
                                # Track what changed (limit field names to reasonable length)
                                field_name = key.replace('_', ' ').title()
                                changes[field_name] = {
                                    'old': str(old_value) if old_value is not None else 'None',
                                    'new': str(value) if value is not None else 'None'
                                }
                                changed = True
                    
                    if changed:
                        existing_product.updated_at = datetime.utcnow()
                        updated += 1
                        updated_products.append({
                            'sku': sku,
                            'name': product_data.get('product_name', sku),
                            'category': category,
                            'changes': changes
                        })
                else:
                    # Add new product
                    product = Product(**product_data)
                    session.add(product)
                    added += 1
                    added_products.append({
                        'sku': sku,
                        'name': product_data.get('product_name', sku),
                        'category': category
                    })
            
            # Commit after each category
            if (added + updated) % 100 == 0:
                session.commit()
                logger.info(f"Progress: {added} new, {updated} updated")
        
        # Find deleted products (in DB but not in Excel)
        deleted_skus = existing_skus - excel_skus
        if deleted_skus:
            logger.info(f"Removing {len(deleted_skus)} products no longer in Excel")
            # Get product details before deletion
            products_to_delete = session.query(Product).filter(Product.sku.in_(deleted_skus)).all()
            for prod in products_to_delete:
                deleted_products.append({
                    'sku': prod.sku,
                    'name': prod.product_name or prod.sku,
                    'category': prod.category
                })
            session.query(Product).filter(Product.sku.in_(deleted_skus)).delete(synchronize_session=False)
            deleted = len(deleted_skus)
        
        session.commit()
        logger.info(f"Database sync complete: {added} added, {updated} updated, {deleted} deleted")
        
        return {
            'products_added': added,
            'products_updated': updated,
            'products_deleted': deleted,
            'added_products': added_products,  # No limit - show all changes
            'updated_products': updated_products,
            'deleted_products': deleted_products
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during database sync: {str(e)}")
        raise
    finally:
        session.close()


def recompute_compatibilities_for_changed_products(changed_skus: Set[str]) -> int:
    """
    Recompute compatibilities for products that changed using bulk operations.
    Creates BIDIRECTIONAL relationships (A→B and B→A) with optimized batching.
    
    Args:
        changed_skus: Set of SKUs that were added or updated
        
    Returns:
        int: Number of compatibility records updated
    """
    if not DB_AVAILABLE or not changed_skus:
        return 0
    
    logger.info(f"Recomputing compatibilities for {len(changed_skus)} changed products")
    
    session = get_session()
    compatibility_count = 0
    
    try:
        # Build SKU to ID mapping for fast lookups
        all_products = session.query(Product.id, Product.sku).all()
        sku_to_id = {p.sku: p.id for p in all_products}
        
        # Collect IDs of products to update
        product_ids_to_update = []
        for sku in changed_skus:
            product_id = sku_to_id.get(sku)
            if product_id:
                product_ids_to_update.append(product_id)
        
        if not product_ids_to_update:
            return 0
        
        # Delete old compatibilities in bulk (both directions)
        logger.info(f"Deleting old compatibilities for {len(product_ids_to_update)} products")
        session.query(ProductCompatibility).filter(
            ProductCompatibility.base_product_id.in_(product_ids_to_update)
        ).delete(synchronize_session=False)
        session.query(ProductCompatibility).filter(
            ProductCompatibility.compatible_product_id.in_(product_ids_to_update)
        ).delete(synchronize_session=False)
        session.commit()
        
        # Prepare batch insert
        BATCH_SIZE = 500
        compatibility_batch = []
        
        for idx, sku in enumerate(changed_skus, 1):
            if idx % 10 == 0:
                logger.info(f"Progress: {idx}/{len(changed_skus)} products processed, {compatibility_count} compatibilities")
            
            product_id = sku_to_id.get(sku)
            if not product_id:
                continue
            
            try:
                # Compute new compatibilities
                results = compatibility.find_compatible_products(sku)
                
                if not results or not results.get('compatibles'):
                    continue
                
                # Store new compatibilities (with deduplication)
                seen_ids = set()
                for category_data in results['compatibles']:
                    for compatible_product_data in category_data.get('products', []):
                        compatible_sku = compatible_product_data.get('sku', '').upper()
                        if not compatible_sku:
                            continue
                        
                        compatible_product_id = sku_to_id.get(compatible_sku)
                        if not compatible_product_id or compatible_product_id in seen_ids:
                            continue
                        
                        seen_ids.add(compatible_product_id)
                        
                        # Add forward relationship to batch (A → B)
                        compatibility_batch.append({
                            'base_product_id': product_id,
                            'compatible_product_id': compatible_product_id,
                            'compatibility_score': 100,
                            'match_reason': f"Compatible {category_data.get('category', 'product')}",
                            'incompatibility_reason': None
                        })
                        
                        # Add reverse relationship to batch (B → A)
                        compatibility_batch.append({
                            'base_product_id': compatible_product_id,
                            'compatible_product_id': product_id,
                            'compatibility_score': 100,
                            'match_reason': f"Reverse: Compatible {category_data.get('category', 'product')}",
                            'incompatibility_reason': None
                        })
                
                # Bulk insert when batch is full
                if len(compatibility_batch) >= BATCH_SIZE:
                    session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
                    session.commit()
                    compatibility_count += len(compatibility_batch)
                    logger.info(f"Inserted batch of {len(compatibility_batch)} compatibilities")
                    compatibility_batch = []
                    
            except Exception as e:
                logger.error(f"Error computing compatibilities for {sku}: {str(e)}")
                continue
        
        # Insert any remaining items in batch
        if compatibility_batch:
            session.bulk_insert_mappings(ProductCompatibility, compatibility_batch)
            session.commit()
            compatibility_count += len(compatibility_batch)
            logger.info(f"Inserted final batch of {len(compatibility_batch)} compatibilities")
        
        logger.info(f"Compatibility recomputation complete: {compatibility_count} records created (bidirectional)")
        
        # Clear API cache after successful compatibility update
        try:
            import app
            if hasattr(app, 'clear_api_cache'):
                app.clear_api_cache()
                logger.info("API cache cleared after compatibility update")
        except Exception as cache_error:
            logger.warning(f"Could not clear API cache: {cache_error}")
        
        return compatibility_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during compatibility recomputation: {str(e)}")
        raise
    finally:
        session.close()


def full_sync_workflow(excel_path: str = None, compute_compatibilities: bool = True) -> dict:
    """
    Complete workflow: sync database and optionally recompute compatibilities.
    
    This is the main function called by the data update service.
    
    Args:
        excel_path: Path to Excel file
        compute_compatibilities: If False, skip compatibility computation (faster for webhooks)
        
    Returns:
        dict: Summary of sync operation with detailed changes
    """
    logger.info(f"Starting database sync workflow (compute_compatibilities={compute_compatibilities})")
    start_time = datetime.now()
    
    try:
        # Step 1: Sync database with Excel
        sync_result = sync_database_from_excel(excel_path)
        added = sync_result['products_added']
        updated = sync_result['products_updated']
        deleted = sync_result['products_deleted']
        
        # Step 2: Optionally recompute compatibilities for changed products
        changed_skus = set()
        compatibility_count = 0
        
        if compute_compatibilities and (added > 0 or updated > 0):
            # Get SKUs of added/updated products
            session = get_session()
            recent_products = session.query(Product.sku).filter(
                Product.updated_at >= start_time
            ).all()
            changed_skus = {p.sku for p in recent_products}
            session.close()
            
            logger.info(f"Computing compatibilities for {len(changed_skus)} changed products")
            compatibility_count = recompute_compatibilities_for_changed_products(changed_skus)
        elif not compute_compatibilities and (added > 0 or updated > 0):
            logger.info(f"Skipping compatibility computation for {added + updated} changed products (fast mode)")
        else:
            compatibility_count = 0
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': True,
            'products_added': added,
            'products_updated': updated,
            'products_deleted': deleted,
            'compatibilities_updated': compatibility_count,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat(),
            # Include detailed change information
            'change_details': {
                'added_products': sync_result.get('added_products', []),
                'updated_products': sync_result.get('updated_products', []),
                'deleted_products': sync_result.get('deleted_products', [])
            }
        }
        
        logger.info(f"Full sync complete in {duration:.1f}s: {added} added, {updated} updated, {deleted} deleted")
        return result
        
    except Exception as e:
        logger.error(f"Full sync workflow failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


if __name__ == '__main__':
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Database sync service')
    parser.add_argument('--sync', action='store_true', help='Run full sync workflow')
    parser.add_argument('--excel-path', type=str, help='Path to Excel file')
    
    args = parser.parse_args()
    
    if args.sync:
        result = full_sync_workflow(args.excel_path)
        print(f"\nSync Result: {result}")
    else:
        print("Usage: python3 db_sync_service.py --sync [--excel-path PATH]")
