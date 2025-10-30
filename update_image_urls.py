#!/usr/bin/env python3
"""
Update product image URLs from a CSV file.

CSV Format:
SKU,Image URL
410001-541-001,https://example.com/images/product1.jpg
105821,https://example.com/images/product2.jpg

Usage:
    python update_image_urls.py image_urls.csv
"""

import sys
import csv
import logging
from models import get_session, Product
from sqlalchemy import update

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_image_urls(csv_file):
    """
    Update product image URLs from a CSV file.
    
    Args:
        csv_file: Path to CSV file with columns: SKU, Image URL
    """
    logger.info("=" * 70)
    logger.info("UPDATE PRODUCT IMAGE URLs")
    logger.info("=" * 70)
    logger.info("")
    
    session = get_session()
    
    try:
        # Read CSV file
        logger.info(f"Reading CSV file: {csv_file}")
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Verify columns
            if 'SKU' not in reader.fieldnames or 'Image URL' not in reader.fieldnames:
                logger.error("CSV must have 'SKU' and 'Image URL' columns")
                logger.error(f"Found columns: {reader.fieldnames}")
                return
            
            updates = []
            for row in reader:
                sku = row['SKU'].strip()
                image_url = row['Image URL'].strip()
                
                if sku and image_url:
                    updates.append({
                        'sku': sku,
                        'image_url': image_url
                    })
        
        logger.info(f"Found {len(updates)} image URLs to update")
        logger.info("")
        
        if not updates:
            logger.warning("No valid updates found in CSV")
            return
        
        # Update products
        updated_count = 0
        not_found = []
        
        for i, update_data in enumerate(updates, 1):
            sku = update_data['sku']
            image_url = update_data['image_url']
            
            # Find product
            product = session.query(Product).filter(Product.sku == sku).first()
            
            if product:
                product.image_url = image_url
                updated_count += 1
                
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(updates)} products processed")
            else:
                not_found.append(sku)
        
        # Commit changes
        session.commit()
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"✓ Updated {updated_count} product image URLs")
        
        if not_found:
            logger.warning(f"⚠ {len(not_found)} SKUs not found in database:")
            for sku in not_found[:10]:  # Show first 10
                logger.warning(f"  - {sku}")
            if len(not_found) > 10:
                logger.warning(f"  ... and {len(not_found) - 10} more")
        
        logger.info("=" * 70)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating image URLs: {e}")
        raise
    finally:
        session.close()


def export_current_urls(output_file='current_image_urls.csv'):
    """
    Export all current product SKUs and image URLs to a CSV file.
    This creates a file you can edit and use with update_image_urls().
    """
    logger.info("=" * 70)
    logger.info("EXPORT CURRENT IMAGE URLs")
    logger.info("=" * 70)
    logger.info("")
    
    session = get_session()
    
    try:
        # Get all products
        products = session.query(Product.sku, Product.product_name, Product.image_url)\
            .order_by(Product.sku)\
            .all()
        
        logger.info(f"Exporting {len(products)} products to {output_file}")
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['SKU', 'Product Name', 'Image URL'])
            
            for product in products:
                writer.writerow([
                    product.sku,
                    product.product_name,
                    product.image_url or ''
                ])
        
        logger.info(f"✓ Exported to {output_file}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Open the CSV file in Excel or a text editor")
        logger.info("2. Update the 'Image URL' column with new URLs")
        logger.info("3. Save the file")
        logger.info("4. Run: python update_image_urls.py current_image_urls.csv")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error exporting URLs: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Export current URLs:  python update_image_urls.py --export")
        print("  Update from CSV:      python update_image_urls.py your_file.csv")
        print("")
        print("Examples:")
        print("  python update_image_urls.py --export")
        print("  python update_image_urls.py image_urls.csv")
        sys.exit(1)
    
    if sys.argv[1] == '--export':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'current_image_urls.csv'
        export_current_urls(output_file)
    else:
        csv_file = sys.argv[1]
        update_image_urls(csv_file)
