import os
import logging
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

USE_DATABASE = os.environ.get('USE_DATABASE', 'auto').lower()

db_available = False
try:
    from models import get_session, Product, ProductCompatibility
    from sqlalchemy.exc import OperationalError, ProgrammingError
    db_available = True
except ImportError as e:
    logger.warning(f"Database models not available: {str(e)}")
    db_available = False


def check_database_ready() -> bool:
    """
    Check if the database is available and has data.
    
    Returns:
        bool: True if database is ready to use, False otherwise
    """
    if not db_available:
        return False
    
    if USE_DATABASE == 'false':
        logger.info("Database usage disabled via USE_DATABASE=false")
        return False
    
    try:
        session = get_session()
        count = session.query(Product).count()
        session.close()
        
        if count > 0:
            logger.info(f"Database ready with {count} products")
            return True
        else:
            logger.info("Database is empty, will use Excel fallback")
            return False
            
    except (OperationalError, ProgrammingError) as e:
        logger.warning(f"Database not ready: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return False


def load_product_from_database(sku: str) -> Optional[Dict]:
    """
    Load a single product from the database.
    
    Args:
        sku (str): Product SKU to load
        
    Returns:
        dict or None: Product data or None if not found
    """
    try:
        session = get_session()
        product = session.query(Product).filter_by(sku=sku.upper()).first()
        session.close()
        
        if not product:
            return None
        
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
            'Product Page URL': product.product_page_url,
            'Image URL': product.image_url,
            'Ranking': product.ranking,
        }
        
        if product.attributes:
            product_dict.update(product.attributes)
        
        return product_dict
        
    except Exception as e:
        logger.error(f"Error loading product from database: {str(e)}")
        return None


def find_product_by_multi_sku(child_sku: str, parent_sku: str = None, unique_id: str = None) -> Optional[Dict]:
    """
    Find a product by searching multiple SKU formats with priority matching.
    Searches in order: child_sku -> parent_sku -> unique_id
    
    Args:
        child_sku (str): Child/variant SKU (highest priority)
        parent_sku (str, optional): Parent SKU (medium priority)
        unique_id (str, optional): Unique ID (lowest priority)
        
    Returns:
        dict with keys: product_data, matched_sku, match_type
        or None if no match found
    """
    try:
        session = get_session()
        
        # Build list of SKUs to search (in order)
        sku_search_list = []
        sku_types = []
        
        if child_sku:
            sku_search_list.append(child_sku.strip().upper())
            sku_types.append('child_sku')
        if parent_sku:
            sku_search_list.append(parent_sku.strip().upper())
            sku_types.append('parent_sku')
        if unique_id:
            sku_search_list.append(unique_id.strip().upper())
            sku_types.append('unique_id')
        
        if not sku_search_list:
            session.close()
            return None
        
        # Single query to search all SKUs at once
        products = session.query(Product).filter(Product.sku.in_(sku_search_list)).all()
        session.close()
        
        if not products:
            return None
        
        # Match by priority: check which SKU matched first
        for i, search_sku in enumerate(sku_search_list):
            for product in products:
                if product.sku == search_sku:
                    # Found match - return with priority info
                    product_dict = {
                        'Unique ID': product.sku,
                        'Product Name': product.product_name,
                        'Brand': product.brand,
                        'Category': product.category,
                        'Series': product.series,
                        'Family': product.family,
                        'Length': float(product.length) if product.length else None,
                        'Width': float(product.width) if product.width else None,
                        'Height': float(product.height) if product.height else None,
                        'Nominal Dimensions': product.nominal_dimensions,
                        'Product Page URL': product.product_page_url,
                        'Image URL': product.image_url,
                        'Ranking': product.ranking,
                    }
                    
                    if product.attributes:
                        product_dict.update(product.attributes)
                    
                    return {
                        'product_data': product_dict,
                        'matched_sku': product.sku,
                        'match_type': sku_types[i]
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Error in multi-SKU lookup: {str(e)}")
        return None


def load_compatible_products_from_database(sku: str) -> Optional[Dict]:
    """
    Load compatible products from the database for a given SKU.
    Optimized with raw SQL for maximum performance.
    
    Args:
        sku (str): Base product SKU
        
    Returns:
        dict or None: Compatibility data or None if not found/not computed
    """
    try:
        from sqlalchemy import text
        from models import get_engine
        
        engine = get_engine()
        
        with engine.connect() as conn:
            # Single optimized SQL query with join - uses idx_base_score index
            result = conn.execute(text("""
                SELECT 
                    p.sku, 
                    p.product_name, 
                    p.brand, 
                    p.series, 
                    p.category,
                    p.product_page_url,
                    p.image_url,
                    p.attributes,
                    pc.compatibility_score
                FROM product_compatibility pc
                JOIN products p ON pc.compatible_product_id = p.id
                WHERE pc.base_product_id = (
                    SELECT id FROM products WHERE sku = :sku LIMIT 1
                )
                AND (pc.incompatibility_reason IS NULL OR pc.incompatibility_reason = '')
                ORDER BY pc.compatibility_score DESC
            """), {"sku": sku.upper()})
            
            rows = result.fetchall()
            
            if not rows:
                logger.info(f"No pre-computed compatibilities for {sku}, will use live computation")
                return None
            
            compatible_products_by_category = {}
            
            for row in rows:
                category = row[4]  # p.category
                
                if category not in compatible_products_by_category:
                    compatible_products_by_category[category] = []
                
                product_data = {
                    'sku': row[0],
                    'name': row[1],
                    'brand': row[2],
                    'series': row[3],
                    'category': category,
                    'product_page_url': row[5],
                    'image_url': row[6],
                    'compatibility_score': row[8],
                }
                
                # Add attributes from JSON field (glass_thickness, door_type, etc.)
                attributes = row[7]  # p.attributes
                if attributes:
                    if 'Glass Thickness' in attributes:
                        product_data['glass_thickness'] = attributes['Glass Thickness']
                    if 'Door Type' in attributes:
                        product_data['door_type'] = attributes['Door Type']
                
                compatible_products_by_category[category].append(product_data)
            
            logger.info(f"Loaded {len(rows)} compatible products from database for {sku}")
            return compatible_products_by_category
        
    except Exception as e:
        logger.error(f"Error loading compatibilities from database: {str(e)}")
        return None


def get_all_products_from_database(category: Optional[str] = None, limit: int = 100, offset: int = 0) -> Tuple[list, int]:
    """
    Get all products from the database with optional filtering and pagination.
    
    Args:
        category (str, optional): Filter by category
        limit (int): Number of products to return
        offset (int): Number of products to skip
        
    Returns:
        tuple: (list of products, total count)
    """
    try:
        session = get_session()
        
        query = session.query(Product)
        if category:
            query = query.filter_by(category=category)
        
        total_count = query.count()
        products = query.offset(offset).limit(limit).all()
        
        product_list = []
        for product in products:
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
                'Product Page URL': product.product_page_url,
                'Image URL': product.image_url,
                'Ranking': product.ranking,
            }
            
            if product.attributes:
                product_dict.update(product.attributes)
            
            product_list.append(product_dict)
        
        session.close()
        return product_list, total_count
        
    except Exception as e:
        logger.error(f"Error getting products from database: {str(e)}")
        return [], 0


def get_data_source_info() -> Dict:
    """
    Get information about the current data source.
    
    Returns:
        dict: Information about data source
    """
    db_ready = check_database_ready()
    
    info = {
        'database_available': db_available,
        'database_ready': db_ready,
        'primary_source': 'database' if db_ready else 'excel',
        'use_database_setting': USE_DATABASE,
    }
    
    if db_ready:
        try:
            session = get_session()
            product_count = session.query(Product).count()
            compatibility_count = session.query(ProductCompatibility).count()
            session.close()
            
            info['database_stats'] = {
                'total_products': product_count,
                'total_compatibilities': compatibility_count,
            }
        except Exception:
            pass
    
    return info


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("Data Source Information:")
    print("-" * 60)
    info = get_data_source_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    if info['database_ready']:
        print("\nTesting database product load...")
        product = load_product_from_database('FB03060M')
        if product:
            print(f"  Found: {product.get('Product Name')}")
        else:
            print("  Product not found in database")
