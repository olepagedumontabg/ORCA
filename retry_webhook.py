#!/usr/bin/env python3
"""
Manual retry script for failed Salsify webhook sync
"""

import requests
from models import get_session
from sqlalchemy import text
import db_sync_service

def retry_failed_webhook():
    session = get_session()
    
    print("Fetching failed webhook data...")
    failed = session.execute(text('''
        SELECT sync_metadata
        FROM sync_status
        WHERE started_at = '2025-11-12 01:05:21.780765'
    ''')).fetchone()
    
    if not failed or not failed[0]:
        print("Error: No failed sync found")
        session.close()
        return False
    
    s3_url = failed[0].get('product_feed_url')
    if not s3_url:
        print("Error: No S3 URL in metadata")
        session.close()
        return False
    
    print(f"\nDownloading from S3...")
    print(f"URL: {s3_url[:70]}...")
    
    response = requests.get(s3_url, timeout=300)
    response.raise_for_status()
    
    excel_path = 'data/Product Data.xlsx'
    with open(excel_path, 'wb') as f:
        f.write(response.content)
    
    file_size = len(response.content) / 1024
    print(f"✅ Downloaded: {file_size:.1f} KB\n")
    
    print("Syncing to database...")
    result = db_sync_service.full_sync_workflow()
    
    print("\n" + "=" * 70)
    print("SYNC COMPLETE!")
    print("=" * 70)
    print(f"Products added:    {result['products_added']}")
    print(f"Products updated:  {result['products_updated']}")
    print(f"Products deleted:  {result['products_deleted']}")
    print(f"Compatibilities:   {result['compatibilities_updated']}")
    print("=" * 70)
    
    session.execute(text('''
        UPDATE sync_status
        SET status = 'completed',
            completed_at = NOW(),
            products_added = :added,
            products_updated = :updated,
            products_deleted = :deleted,
            compatibilities_updated = :compat,
            error_message = NULL
        WHERE started_at = '2025-11-12 01:05:21.780765'
    '''), {
        'added': result['products_added'],
        'updated': result['products_updated'],
        'deleted': result['products_deleted'],
        'compat': result['compatibilities_updated']
    })
    session.commit()
    session.close()
    
    print("\n✅ Sync record updated in database")
    return True

if __name__ == '__main__':
    retry_failed_webhook()
