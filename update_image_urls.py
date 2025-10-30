#!/usr/bin/env python3
"""
Update product image URLs in both database and Excel file from a CSV file.

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
import pandas as pd
import shutil
from datetime import datetime
from models import get_session, Product
from sqlalchemy import update

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

EXCEL_FILE = 'data/Product Data.xlsx'


def update_image_urls(csv_file):
    """
    Update product image URLs in both database and Excel file from a CSV file.
    
    Args:
        csv_file: Path to CSV file with columns: SKU, Image URL
    """
    logger.info("=" * 70)
    logger.info("UPDATE PRODUCT IMAGE URLs (DATABASE + EXCEL)")
    logger.info("=" * 70)
    logger.info("")
    
    # Read CSV file
    logger.info(f"Reading CSV file: {csv_file}")
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # Verify columns
        if 'SKU' not in reader.fieldnames or 'Image URL' not in reader.fieldnames:
            logger.error("CSV must have 'SKU' and 'Image URL' columns")
            logger.error(f"Found columns: {reader.fieldnames}")
            return
        
        updates = {}
        for row in reader:
            sku = row['SKU'].strip()
            image_url = row['Image URL'].strip()
            
            if sku and image_url:
                updates[sku] = image_url
    
    logger.info(f"Found {len(updates)} image URLs to update")
    logger.info("")
    
    if not updates:
        logger.warning("No valid updates found in CSV")
        return
    
    # Step 1: Update Database
    logger.info("Step 1: Updating database...")
    db_updated = update_database(updates)
    
    # Step 2: Update Excel File
    logger.info("")
    logger.info("Step 2: Updating Excel file...")
    excel_updated = update_excel_file(updates)
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("UPDATE SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Database: {db_updated} products updated")
    logger.info(f"Excel:    {excel_updated} products updated")
    logger.info("")
    logger.info("✓ Image URLs updated successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Restart the app to reload the Excel file")
    logger.info("2. (Optional) Sync to production: python sync_to_production.py")
    logger.info("=" * 70)


def update_database(updates):
    """Update image URLs in the database."""
    session = get_session()
    updated_count = 0
    not_found = []
    
    try:
        for i, (sku, image_url) in enumerate(updates.items(), 1):
            product = session.query(Product).filter(Product.sku == sku).first()
            
            if product:
                product.image_url = image_url
                updated_count += 1
                
                if i % 100 == 0:
                    logger.info(f"  Database progress: {i}/{len(updates)}")
            else:
                not_found.append(sku)
        
        session.commit()
        logger.info(f"  ✓ Database: {updated_count} products updated")
        
        if not_found:
            logger.warning(f"  ⚠ {len(not_found)} SKUs not found in database")
            for sku in not_found[:5]:
                logger.warning(f"    - {sku}")
            if len(not_found) > 5:
                logger.warning(f"    ... and {len(not_found) - 5} more")
        
        return updated_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating database: {e}")
        raise
    finally:
        session.close()


def update_excel_file(updates):
    """Update image URLs in the Excel file."""
    try:
        # Backup the original file
        backup_file = f"{EXCEL_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(EXCEL_FILE, backup_file)
        logger.info(f"  Created backup: {backup_file}")
        
        # Read all sheets into memory first (before opening writer)
        excel_file = pd.ExcelFile(EXCEL_FILE, engine='openpyxl')
        sheet_names = excel_file.sheet_names
        logger.info(f"  Processing {len(sheet_names)} sheets...")
        
        total_updated = 0
        updated_sheets = {}
        
        # Load all sheets into memory
        all_sheets = {}
        for sheet_name in sheet_names:
            all_sheets[sheet_name] = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Close the reader before opening the writer
        excel_file.close()
        
        # Process and write all sheets
        with pd.ExcelWriter(EXCEL_FILE, engine='xlsxwriter') as writer:
            for sheet_name in sheet_names:
                df = all_sheets[sheet_name]
                
                # Check if sheet has the required columns
                if 'Unique ID' not in df.columns or 'Image URL' not in df.columns:
                    # Write sheet as-is
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    continue
                
                # Update image URLs
                sheet_updated = 0
                for idx, row in df.iterrows():
                    sku = str(row['Unique ID']).strip()
                    if sku in updates:
                        df.at[idx, 'Image URL'] = updates[sku]
                        sheet_updated += 1
                
                if sheet_updated > 0:
                    updated_sheets[sheet_name] = sheet_updated
                    total_updated += sheet_updated
                
                # Write updated sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"  ✓ Excel: {total_updated} products updated across {len(updated_sheets)} sheets")
        
        if updated_sheets:
            for sheet, count in updated_sheets.items():
                logger.info(f"    - {sheet}: {count} products")
        
        return total_updated
        
    except Exception as e:
        logger.error(f"Error updating Excel file: {e}")
        raise


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
