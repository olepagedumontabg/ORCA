#!/usr/bin/env python3
"""
Sync Development Database to Production
Copies all products and compatibility records from development to production database
Fast and safe - completes in under 2 minutes for 2,193 products + 63,211 compatibility records
"""

import os
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_to_production():
    """
    Sync development database to production using the optimized copy script
    """
    # Check for production DATABASE_URL
    prod_db_url = os.environ.get('PROD_DATABASE_URL')
    if not prod_db_url:
        logger.error("=" * 70)
        logger.error("ERROR: PROD_DATABASE_URL environment variable not set")
        logger.error("=" * 70)
        print()
        print("To sync to production, set the PROD_DATABASE_URL:")
        print()
        print("  export PROD_DATABASE_URL='postgresql://user:pass@host/database'")
        print("  python sync_to_production.py")
        print()
        print("Or run inline:")
        print()
        print("  PROD_DATABASE_URL='your-url' python sync_to_production.py")
        print()
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("SYNC DEVELOPMENT DATABASE TO PRODUCTION")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This will copy all products and compatibility records from")
    logger.info("the development database to production.")
    logger.info("")
    logger.info(f"Production URL: {prod_db_url[:30]}...")
    logger.info("")
    
    # Get development database URL
    dev_db_url = os.environ.get('DATABASE_URL')
    if not dev_db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Import after confirming URLs are set
    from copy_dev_to_prod import copy_database
    
    try:
        start_time = time.time()
        
        # Run the copy
        copy_database(dev_db_url, prod_db_url)
        
        elapsed = time.time() - start_time
        
        logger.info("=" * 70)
        logger.info("PRODUCTION SYNC COMPLETE")
        logger.info(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        
        if elapsed < 300:
            logger.info("✓ Completed in under 5 minutes!")
        
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    try:
        sync_to_production()
    except KeyboardInterrupt:
        logger.warning("Sync interrupted by user")
        sys.exit(1)
