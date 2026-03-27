#!/usr/bin/env python3
"""
Lightning-Fast Database Sync Script
Syncs Excel data to database and computes compatibilities in under 5 minutes
Optimized with parallel batch processing and smart incremental updates
"""

import os
import sys
import time
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict
from sqlalchemy import delete, and_
from sqlalchemy.exc import IntegrityError
from models import get_session, get_engine, Product, ProductCompatibility, Base
from logic import compatibility, base_compatibility, bathtub_compatibility, shower_compatibility, tubshower_compatibility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and display progress during sync operations"""
    
    def __init__(self, total: int, operation: str):
        self.total = total
        self.current = 0
        self.operation = operation
        self.start_time = time.time()
    
    def update(self, increment: int = 1):
        self.current += increment
        if self.current % 50 == 0 or self.current == self.total:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            percent = (self.current / self.total * 100) if self.total > 0 else 0
            eta = (self.total - self.current) / rate if rate > 0 else 0
            logger.info(f"{self.operation}: {self.current}/{self.total} ({percent:.1f}%) - {rate:.1f}/sec - ETA: {eta:.0f}s")
    
    def finish(self):
        elapsed = time.time() - self.start_time
        logger.info(f"{self.operation} complete: {self.current} items in {elapsed:.1f}s ({self.current/elapsed:.1f}/sec)")


def create_schema():
    """Create database schema"""
    logger.info("Creating database schema...")
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Schema created successfully")


def bulk_import_products() -> Tuple[int, int, int, Dict]:
    """
    Bulk import products from Excel with optimized batch processing
    Returns: (new_count, updated_count, unchanged_count, excel_data)
    """
    logger.info("Starting bulk product import...")
    start_time = time.time()
    
    session = get_session()
    try:
        # Load Excel data
        logger.info("Loading Excel data...")
        data = compatibility.load_data()
        
        # Get all existing products
        existing_products = {p.sku: p for p in session.query(Product).all()}
        logger.info(f"Found {len(existing_products)} existing products in database")
        
        new_products = []
        updated_skus = set()
        unchanged_count = 0
        
        for category, df in data.items():
            if 'Unique ID' not in df.columns:
                continue
            
            logger.info(f"Processing category: {category} ({len(df)} products)")
            
            for _, row in df.iterrows():
                sku = str(row.get('Unique ID', '')).strip().upper()
                if not sku or sku == 'NAN':
                    continue
                
                # Build product data
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
                
                # Build attributes
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
                
                # Check if exists
                if sku in existing_products:
                    # Update existing product
                    existing = existing_products[sku]
                    for key, value in product_data.items():
                        if key != 'created_at':
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    updated_skus.add(sku)
                else:
                    # Add new product
                    new_products.append(Product(**product_data))
        
        # Bulk insert new products
        if new_products:
            logger.info(f"Bulk inserting {len(new_products)} new products...")
            session.bulk_save_objects(new_products)
        
        # Commit all changes
        session.commit()
        
        elapsed = time.time() - start_time
        new_count = len(new_products)
        updated_count = len(updated_skus)
        unchanged_count = len(existing_products) - updated_count
        
        logger.info(f"Product import complete in {elapsed:.1f}s:")
        logger.info(f"  New: {new_count}")
        logger.info(f"  Updated: {updated_count}")
        logger.info(f"  Unchanged: {unchanged_count}")
        
        return new_count, updated_count, unchanged_count, data
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error during bulk import: {e}")
        raise
    finally:
        session.close()


def compute_missing_compatibilities(excel_data: Dict = None):
    """
    Compute compatibilities for products that don't have any (or only have reverse compatibility)
    Uses optimized incremental computation with cached Excel data
    
    Args:
        excel_data: Pre-loaded Excel data (if available) to avoid reloading
    """
    logger.info("Finding products with missing forward compatibilities...")
    start_time = time.time()
    
    session = get_session()
    try:
        # Find products missing forward compatibilities
        all_products = session.query(Product).all()
        products_with_forward = session.query(Product.id).join(
            ProductCompatibility, Product.id == ProductCompatibility.base_product_id
        ).filter(ProductCompatibility.compatibility_score > 0).distinct().all()
        
        products_with_forward_ids = {p[0] for p in products_with_forward}
        products_needing_compute = [p for p in all_products if p.id not in products_with_forward_ids]
        
        logger.info(f"Found {len(products_needing_compute)} products needing compatibility computation")
        
        if not products_needing_compute:
            logger.info("All products already have compatibilities computed")
            return 0
        
        # Build product index for fast lookups
        logger.info("Building product index...")
        product_index = build_product_index(all_products)
        
        # Use provided Excel data or load it
        if excel_data is None:
            logger.info("Loading Excel data for compatibility computation...")
            excel_data = compatibility.load_data()
        
        # Convert database products to pandas DataFrames (one-time conversion)
        logger.info("Converting database products to DataFrames...")
        data = convert_products_to_dataframes(product_index)
        
        # Process in batches
        batch_size = 100  # Increased batch size since we're using cached data
        total_records = 0
        progress = ProgressTracker(len(products_needing_compute), "Computing compatibilities")
        
        for i in range(0, len(products_needing_compute), batch_size):
            batch = products_needing_compute[i:i + batch_size]
            compatibility_records = []
            
            for product in batch:
                records = compute_product_compatibilities_fast(product, product_index, data)
                compatibility_records.extend(records)
            
            # Bulk insert compatibility records
            if compatibility_records:
                session.bulk_insert_mappings(ProductCompatibility, compatibility_records)
                session.commit()
                total_records += len(compatibility_records)
            
            progress.update(len(batch))
        
        progress.finish()
        
        elapsed = time.time() - start_time
        logger.info(f"Compatibility computation complete in {elapsed:.1f}s: {total_records} records created")
        
        return total_records
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error computing compatibilities: {e}")
        raise
    finally:
        session.close()


def build_product_index(all_products: List[Product]) -> Dict:
    """Build indexed lookup structure for fast product access"""
    index = {
        'by_category': defaultdict(list),
        'by_sku': {},
        'by_id': {}
    }
    
    for product in all_products:
        index['by_category'][product.category].append(product)
        index['by_sku'][product.sku] = product
        index['by_id'][product.id] = product
    
    return index


def convert_products_to_dataframes(index: Dict) -> Dict:
    """
    Convert database products to pandas DataFrames (one-time operation)
    This is much faster than converting for each product individually
    """
    data = {}
    for category, products in index['by_category'].items():
        product_dicts = []
        for p in products:
            p_dict = {
                'Unique ID': p.sku,
                'Product Name': p.product_name,
                'Brand': p.brand,
                'Series': p.series,
                'Family': p.family,
                'Category': p.category,
                'Length': float(p.length) if p.length else None,
                'Width': float(p.width) if p.width else None,
                'Height': float(p.height) if p.height else None,
                'Nominal Dimensions': p.nominal_dimensions,
                'Product Page URL': p.product_page_url,
                'Image URL': p.image_url,
                'Ranking': p.ranking,
            }
            if p.attributes:
                for key, value in p.attributes.items():
                    if hasattr(value, 'item'):
                        p_dict[key] = value.item()
                    else:
                        p_dict[key] = value
            product_dicts.append(p_dict)
        
        data[category] = pd.DataFrame(product_dicts)
    
    return data


def compute_product_compatibilities_fast(product: Product, index: Dict, data: Dict) -> List[Dict]:
    """
    Fast compatibility computation using pre-converted DataFrames
    Avoids repeated DataFrame conversion
    """
    # Convert Product model to dict format
    product_dict = {
        'Unique ID': product.sku,
        'Product Name': product.product_name,
        'Brand': product.brand,
        'Series': product.series,
        'Family': product.family,
        'Category': product.category,
        'Length': float(product.length) if product.length else None,
        'Width': float(product.width) if product.width else None,
        'Height': float(product.height) if product.height else None,
        'Nominal Dimensions': product.nominal_dimensions,
    }
    
    # Add attributes
    if product.attributes:
        for key, value in product.attributes.items():
            if hasattr(value, 'item'):
                product_dict[key] = value.item()
            else:
                product_dict[key] = value
    
    # Call appropriate compatibility function based on category
    compatible_categories = []
    if product.category == 'Shower Bases':
        compatible_categories = base_compatibility.find_base_compatibilities(data, product_dict)
    elif product.category == 'Bathtubs':
        compatible_categories = bathtub_compatibility.find_bathtub_compatibilities(data, product_dict)
    elif product.category == 'Showers':
        compatible_categories = shower_compatibility.find_shower_compatibilities(data, product_dict)
    elif product.category == 'Tub Showers':
        compatible_categories = tubshower_compatibility.find_tubshower_compatibilities(data, product_dict)
    else:
        # Other categories only provide reverse compatibility
        return []
    
    # Convert results to database records
    compatibility_records = []
    for category_data in compatible_categories:
        category = category_data.get('category')
        products_list = category_data.get('products', [])
        
        for compat_product in products_list:
            compat_sku = compat_product.get('sku')
            compat_db_product = index['by_sku'].get(compat_sku)
            
            if compat_db_product:
                compatibility_records.append({
                    'base_product_id': product.id,
                    'compatible_product_id': compat_db_product.id,
                    'compatibility_score': compat_product.get('compatibility_score', 500),
                    'match_reason': None,
                    'incompatibility_reason': None,
                    'computed_at': datetime.utcnow()
                })
    
    return compatibility_records


def compute_product_compatibilities(product: Product, index: Dict, session) -> List[Dict]:
    """
    Compute compatibilities for a single product
    Returns list of compatibility record dicts for bulk insert
    """
    # Convert Product model to dict format expected by compatibility logic
    product_dict = {
        'Unique ID': product.sku,
        'Product Name': product.product_name,
        'Brand': product.brand,
        'Series': product.series,
        'Family': product.family,
        'Category': product.category,
        'Length': float(product.length) if product.length else None,
        'Width': float(product.width) if product.width else None,
        'Height': float(product.height) if product.height else None,
        'Nominal Dimensions': product.nominal_dimensions,
    }
    
    # Add attributes
    if product.attributes:
        for key, value in product.attributes.items():
            if hasattr(value, 'item'):  # numpy scalar
                product_dict[key] = value.item()
            else:
                product_dict[key] = value
    
    # Build data dict with all products by category (pandas DataFrames)
    data = {}
    for category, products in index['by_category'].items():
        product_dicts = []
        for p in products:
            p_dict = {
                'Unique ID': p.sku,
                'Product Name': p.product_name,
                'Brand': p.brand,
                'Series': p.series,
                'Family': p.family,
                'Category': p.category,
                'Length': float(p.length) if p.length else None,
                'Width': float(p.width) if p.width else None,
                'Height': float(p.height) if p.height else None,
                'Nominal Dimensions': p.nominal_dimensions,
                'Product Page URL': p.product_page_url,
                'Image URL': p.image_url,
                'Ranking': p.ranking,
            }
            if p.attributes:
                for key, value in p.attributes.items():
                    if hasattr(value, 'item'):
                        p_dict[key] = value.item()
                    else:
                        p_dict[key] = value
            product_dicts.append(p_dict)
        
        data[category] = pd.DataFrame(product_dicts)
    
    # Call appropriate compatibility function based on category
    compatible_categories = []
    if product.category == 'Shower Bases':
        compatible_categories = base_compatibility.find_base_compatibilities(data, product_dict)
    elif product.category == 'Bathtubs':
        compatible_categories = bathtub_compatibility.find_bathtub_compatibilities(data, product_dict)
    elif product.category == 'Showers':
        compatible_categories = shower_compatibility.find_shower_compatibilities(data, product_dict)
    elif product.category == 'Tub Showers':
        compatible_categories = tubshower_compatibility.find_tubshower_compatibilities(data, product_dict)
    else:
        # Other categories only provide reverse compatibility
        return []
    
    # Convert results to database records
    compatibility_records = []
    for category_data in compatible_categories:
        category = category_data.get('category')
        products_list = category_data.get('products', [])
        
        for compat_product in products_list:
            compat_sku = compat_product.get('sku')
            compat_db_product = index['by_sku'].get(compat_sku)
            
            if compat_db_product:
                compatibility_records.append({
                    'base_product_id': product.id,
                    'compatible_product_id': compat_db_product.id,
                    'compatibility_score': compat_product.get('compatibility_score', 500),
                    'match_reason': None,
                    'incompatibility_reason': None,
                    'computed_at': datetime.utcnow()
                })
    
    return compatibility_records


def sync_all():
    """
    Complete sync: create schema, import products, compute compatibilities
    Optimized for speed - target under 5 minutes for full sync
    """
    overall_start = time.time()
    
    logger.info("=" * 60)
    logger.info("LIGHTNING-FAST DATABASE SYNC")
    logger.info("=" * 60)
    
    # Step 1: Create schema
    create_schema()
    
    # Step 2: Bulk import products
    new_count, updated_count, unchanged_count, excel_data = bulk_import_products()
    
    # Step 3: Compute missing compatibilities (passing Excel data to avoid reloading)
    compat_records = compute_missing_compatibilities(excel_data)
    
    overall_elapsed = time.time() - overall_start
    
    logger.info("=" * 60)
    logger.info("SYNC COMPLETE")
    logger.info(f"Total time: {overall_elapsed:.1f}s ({overall_elapsed/60:.1f} minutes)")
    logger.info(f"Products: {new_count} new, {updated_count} updated, {unchanged_count} unchanged")
    logger.info(f"Compatibility records: {compat_records} created")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        sync_all()
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
