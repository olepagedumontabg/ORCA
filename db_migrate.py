import os
import sys
import pandas as pd
import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import get_session, get_engine, Product, ProductCompatibility, CompatibilityOverride, Base
from logic import compatibility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_schema():
    """
    Create all database tables.
    """
    logger.info("Creating database schema...")
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database schema created successfully")


def import_products_from_excel():
    """
    Import all products from Excel files into the database.
    
    Returns:
        int: Number of products imported
    """
    logger.info("Starting product import from Excel...")
    session = get_session()
    imported_count = 0
    updated_count = 0
    
    try:
        data = compatibility.load_data()
        
        for category, df in data.items():
            if 'Unique ID' not in df.columns:
                logger.warning(f"Skipping category '{category}' - no 'Unique ID' column")
                continue
            
            logger.info(f"Processing category: {category} ({len(df)} products)")
            
            for _, row in df.iterrows():
                sku = str(row.get('Unique ID', '')).strip().upper()
                if not sku or sku == 'NAN':
                    continue
                
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
                
                existing_product = session.query(Product).filter_by(sku=sku).first()
                
                if existing_product:
                    for key, value in product_data.items():
                        if key != 'created_at':
                            setattr(existing_product, key, value)
                    existing_product.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    product = Product(**product_data)
                    session.add(product)
                    imported_count += 1
                
                if (imported_count + updated_count) % 100 == 0:
                    session.commit()
                    logger.info(f"Progress: {imported_count} new, {updated_count} updated")
        
        session.commit()
        logger.info(f"Product import complete: {imported_count} new products, {updated_count} updated")
        return imported_count + updated_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error importing products: {str(e)}")
        raise
    finally:
        session.close()


def compute_compatibilities(limit=None, sku_filter=None):
    """
    Compute and store product compatibilities in the database.
    
    Args:
        limit (int, optional): Limit the number of products to process
        sku_filter (str, optional): Only process products matching this SKU
    
    Returns:
        int: Number of compatibility records created
    """
    logger.info("Starting compatibility computation...")
    
    # CRITICAL: Load data into memory ONCE before processing all products
    # This prevents reloading Excel files 2,193+ times (6 seconds each!)
    logger.info("Preloading product data into memory cache...")
    try:
        import data_update_service
        excel_path = os.path.join('data', 'Product Data.xlsx')
        if not data_update_service.load_data_into_memory(excel_path):
            logger.error("Failed to preload data into memory")
            return 0
        logger.info("Data successfully preloaded - compatibility computation will be FAST!")
    except Exception as e:
        logger.error(f"Error preloading data: {str(e)}")
        return 0
    
    session = get_session()
    compatibility_count = 0
    
    try:
        query = session.query(Product)
        if sku_filter:
            query = query.filter(Product.sku == sku_filter.upper())
        if limit:
            query = query.limit(limit)
        
        products = query.all()
        total_products = len(products)
        
        logger.info(f"Processing {total_products} products for compatibility...")
        
        for idx, product in enumerate(products, 1):
            if idx % 10 == 0:
                logger.info(f"Progress: {idx}/{total_products} products processed, {compatibility_count} compatibilities found")
            
            session.query(ProductCompatibility).filter_by(base_product_id=product.id).delete()
            
            try:
                results = compatibility.find_compatible_products(product.sku)
                
                if not results or not results.get('compatibles'):
                    continue
                
                for category_data in results['compatibles']:
                    for compatible_product_data in category_data.get('products', []):
                        compatible_sku = compatible_product_data.get('sku', '').upper()
                        if not compatible_sku:
                            continue
                        
                        compatible_product = session.query(Product).filter_by(sku=compatible_sku).first()
                        if not compatible_product:
                            continue
                        
                        compatibility_record = ProductCompatibility(
                            base_product_id=product.id,
                            compatible_product_id=compatible_product.id,
                            compatibility_score=100,
                            match_reason=f"Compatible {category_data.get('category', 'product')}",
                            incompatibility_reason=None
                        )
                        session.add(compatibility_record)
                        compatibility_count += 1
                
                if idx % 10 == 0:
                    session.commit()
                    
            except Exception as e:
                logger.error(f"Error processing product {product.sku}: {str(e)}")
                continue
        
        session.commit()
        logger.info(f"Compatibility computation complete: {compatibility_count} records created")
        return compatibility_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error computing compatibilities: {str(e)}")
        raise
    finally:
        session.close()


def get_stats():
    """
    Get database statistics.
    
    Returns:
        dict: Database statistics
    """
    session = get_session()
    try:
        from sqlalchemy import func
        
        total_products = session.query(Product).count()
        total_compatibilities = session.query(ProductCompatibility).count()
        products_with_compat = session.query(ProductCompatibility.base_product_id).distinct().count()
        
        stats = {
            'total_products': total_products,
            'total_compatibilities': total_compatibilities,
            'total_overrides': session.query(CompatibilityOverride).count(),
            'products_with_compatibilities': products_with_compat,
            'products_without_compatibilities': total_products - products_with_compat,
            'avg_compatibilities': total_compatibilities / products_with_compat if products_with_compat > 0 else 0,
            'products_by_category': {}
        }
        
        category_counts = session.query(
            Product.category,
            func.count(Product.id)
        ).group_by(Product.category).all()
        
        for category, count in category_counts:
            stats['products_by_category'][category] = count
        
        return stats
    finally:
        session.close()


def main():
    """
    Main migration script.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Database migration and management')
    parser.add_argument('--create-schema', action='store_true', help='Create database schema')
    parser.add_argument('--import-products', action='store_true', help='Import products from Excel')
    parser.add_argument('--compute-compatibilities', action='store_true', help='Compute product compatibilities')
    parser.add_argument('--limit', type=int, help='Limit number of products to process')
    parser.add_argument('--sku', type=str, help='Process only this SKU')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--full-migration', action='store_true', help='Run full migration (schema + import + compute)')
    
    args = parser.parse_args()
    
    if args.full_migration:
        logger.info("Running full migration...")
        create_schema()
        import_products_from_excel()
        logger.info("Computing compatibilities for first 50 products as test...")
        compute_compatibilities(limit=50)
        stats = get_stats()
        logger.info(f"Migration complete! Stats: {stats}")
        
    else:
        if args.create_schema:
            create_schema()
        
        if args.import_products:
            import_products_from_excel()
        
        if args.compute_compatibilities:
            compute_compatibilities(limit=args.limit, sku_filter=args.sku)
        
        if args.stats:
            stats = get_stats()
            logger.info("Database Statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")


if __name__ == '__main__':
    main()
