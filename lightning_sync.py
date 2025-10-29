#!/usr/bin/env python3
"""
Lightning-Fast Production Database Sync
Ultra-simple approach: Use existing optimized scripts with production DATABASE_URL
Target: Under 5 minutes for 2,193 products + 60K+ compatibility records
"""

import os
import sys
import time
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_with_prod_db(script_path: str, description: str) -> float:
    """
    Run a script with production DATABASE_URL
    Returns elapsed time in seconds
    """
    prod_db_url = os.environ.get('PROD_DATABASE_URL')
    if not prod_db_url:
        logger.error("PROD_DATABASE_URL environment variable not set")
        logger.error("Please set it to your production database connection string")
        sys.exit(1)
    
    logger.info(f"Running: {description}")
    start_time = time.time()
    
    env = os.environ.copy()
    env['DATABASE_URL'] = prod_db_url
    
    try:
        result = subprocess.run(
            ['python', script_path],
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✓ {description} complete in {elapsed:.1f}s")
        
        # Show last few lines of output
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-5:]:
            logger.info(f"  {line}")
        
        return elapsed
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ {description} failed after {elapsed:.1f}s")
        logger.error(f"Error: {e.stderr}")
        sys.exit(1)


def sync_to_production():
    """
    Lightning-fast production sync using existing optimized scripts
    """
    overall_start = time.time()
    
    logger.info("=" * 70)
    logger.info("LIGHTNING-FAST PRODUCTION DATABASE SYNC")
    logger.info("=" * 70)
    
    # Step 1: Sync products from Excel to database (also handles schema creation)
    logger.info("Step 1/2: Syncing products from Excel to production database...")
    sync_time = run_with_prod_db('db_sync_service.py', 'Product sync')
    
    # Step 2: Compute compatibilities for products that need them
    logger.info("Step 2/2: Computing missing compatibilities...")
    compat_time = run_with_prod_db('add_products.py', 'Compatibility computation')
    
    overall_elapsed = time.time() - overall_start
    
    logger.info("=" * 70)
    logger.info("PRODUCTION SYNC COMPLETE")
    logger.info(f"Total time: {overall_elapsed:.1f}s ({overall_elapsed/60:.1f} minutes)")
    logger.info(f"  Product sync: {sync_time:.1f}s")
    logger.info(f"  Compatibility computation: {compat_time:.1f}s")
    logger.info("=" * 70)
    
    if overall_elapsed < 300:
        logger.info(f"✓ GOAL ACHIEVED: Completed in under 5 minutes!")
    else:
        logger.warning(f"⚠ Took longer than 5 minute goal, but database is synced")


if __name__ == '__main__':
    # Check for required environment variable
    if 'PROD_DATABASE_URL' not in os.environ:
        print("=" * 70)
        print("ERROR: PROD_DATABASE_URL environment variable not set")
        print("=" * 70)
        print()
        print("To sync to production, set the PROD_DATABASE_URL:")
        print()
        print("  export PROD_DATABASE_URL='your-production-database-url'")
        print("  python lightning_sync.py")
        print()
        print("Or run inline:")
        print()
        print("  PROD_DATABASE_URL='your-url' python lightning_sync.py")
        print()
        sys.exit(1)
    
    try:
        sync_to_production()
    except KeyboardInterrupt:
        logger.warning("Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
