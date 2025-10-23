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


def load_compatible_products_from_database(sku: str) -> Optional[Dict]:
    """
    Load compatible products from the database for a given SKU.
    
    Args:
        sku (str): Base product SKU
        
    Returns:
        dict or None: Compatibility data or None if not found/not computed
    """
    try:
        session = get_session()
        
        product = session.query(Product).filter_by(sku=sku.upper()).first()
        if not product:
            session.close()
            return None
        
        from sqlalchemy import or_
        
        compatibilities = session.query(ProductCompatibility).filter(
            ProductCompatibility.base_product_id == product.id,
            or_(
                ProductCompatibility.incompatibility_reason == None,
                ProductCompatibility.incompatibility_reason == ''
            )
        ).all()
        
        if not compatibilities:
            logger.info(f"No pre-computed compatibilities for {sku}, will use live computation")
            session.close()
            return None
        
        compatible_products_by_category = {}
        
        for comp in compatibilities:
            comp_product = comp.compatible_product
            category = comp_product.category
            
            if category not in compatible_products_by_category:
                compatible_products_by_category[category] = []
            
            product_data = {
                'sku': comp_product.sku,
                'name': comp_product.product_name,
                'brand': comp_product.brand,
                'series': comp_product.series,
                'category': comp_product.category,
                'product_page_url': comp_product.product_page_url,
                'image_url': comp_product.image_url,
                'compatibility_score': comp.compatibility_score,
            }
            
            # Add attributes from JSON field (glass_thickness, door_type, etc.)
            if comp_product.attributes:
                if 'Glass Thickness' in comp_product.attributes:
                    product_data['glass_thickness'] = comp_product.attributes['Glass Thickness']
                if 'Door Type' in comp_product.attributes:
                    product_data['door_type'] = comp_product.attributes['Door Type']
            
            compatible_products_by_category[category].append(product_data)
        
        session.close()
        
        logger.info(f"Loaded {len(compatibilities)} compatible products from database for {sku}")
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
