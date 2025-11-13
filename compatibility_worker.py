"""
Automatic compatibility computation worker.

This background worker:
1. Runs continuously inside the app
2. Checks for products missing compatibilities every 2 minutes
3. Automatically computes them in small batches
4. Survives app restarts by saving progress to database
"""

import logging
import time
import threading
from datetime import datetime
from models import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class CompatibilityWorker:
    """Background worker that automatically computes missing compatibilities."""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.check_interval = 120  # Check every 2 minutes
        self.batch_size = 50  # Process 50 products at a time
        
    def start(self):
        """Start the background worker thread."""
        if self.running:
            logger.warning("Compatibility worker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        logger.info("Compatibility worker started (checking every 2 minutes)")
    
    def stop(self):
        """Stop the background worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Compatibility worker stopped")
    
    def _worker_loop(self):
        """Main worker loop - checks for missing compatibilities and computes them."""
        logger.info("Compatibility worker loop started")
        
        # Wait 30 seconds on startup to let app initialize
        time.sleep(30)
        
        while self.running:
            try:
                self._check_and_compute()
            except Exception as e:
                logger.error(f"Compatibility worker error: {e}")
            
            # Wait before next check
            time.sleep(self.check_interval)
    
    def _check_and_compute(self):
        """Check for products without compatibilities and compute them."""
        session = get_session()
        
        try:
            # Count products without compatibilities
            products_without = session.execute(text('''
                SELECT COUNT(DISTINCT p.id)
                FROM products p
                LEFT JOIN product_compatibility pc ON p.id = pc.base_product_id
                WHERE pc.base_product_id IS NULL
            ''')).fetchone()[0]
            
            if products_without == 0:
                # All products have compatibilities - nothing to do
                session.close()
                return
            
            logger.info(f"Found {products_without} products without compatibilities - starting computation")
            
            # Get SKUs of products without compatibilities (limited batch)
            products_to_process = session.execute(text('''
                SELECT p.sku
                FROM products p
                LEFT JOIN product_compatibility pc ON p.id = pc.base_product_id
                WHERE pc.base_product_id IS NULL
                ORDER BY p.id
                LIMIT :batch_size
            '''), {'batch_size': self.batch_size}).fetchall()
            
            skus_to_process = [p[0] for p in products_to_process]
            session.close()
            
            if not skus_to_process:
                return
            
            # Compute compatibilities for this batch
            logger.info(f"Computing compatibilities for batch of {len(skus_to_process)} products")
            
            import db_sync_service
            from models import Product
            
            # Process each SKU
            session = get_session()
            for sku in skus_to_process:
                try:
                    # Use the existing recompute function for just this SKU
                    db_sync_service.recompute_compatibilities_for_changed_products({sku})
                except Exception as e:
                    logger.error(f"Error computing compatibility for SKU {sku}: {e}")
            
            session.close()
            
            logger.info(f"Completed batch of {len(skus_to_process)} products. Remaining: {products_without - len(skus_to_process)}")
            
            # If there are more to process, run again immediately
            if products_without > len(skus_to_process):
                logger.info("More products to process - continuing immediately")
                time.sleep(5)  # Short delay between batches
                self._check_and_compute()
                
        except Exception as e:
            logger.error(f"Error in compatibility check: {e}")
            if session:
                session.close()

# Global worker instance
_worker = None

def start_worker():
    """Start the global compatibility worker."""
    global _worker
    if _worker is None:
        _worker = CompatibilityWorker()
    _worker.start()

def stop_worker():
    """Stop the global compatibility worker."""
    global _worker
    if _worker:
        _worker.stop()
