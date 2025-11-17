"""
Automatic compatibility computation worker.

This background worker:
1. Runs continuously inside the app
2. Checks for queued Salsify webhooks and processes them
3. Checks for products missing compatibilities every 2 minutes
4. Automatically computes them in small batches
5. Survives app restarts by using file-based queue
"""

import logging
import time
import threading
import os
import json
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
        """Main worker loop - processes webhooks and computes compatibilities."""
        logger.info("Compatibility worker loop started")
        
        # Clean up any syncs stuck in 'processing' from app crash/restart
        self._cleanup_stuck_syncs()
        
        # Wait 30 seconds on startup to let app initialize
        time.sleep(30)
        
        while self.running:
            try:
                # First priority: Process queued webhooks
                self._process_queued_webhooks()
                
                # Second priority: Compute missing compatibilities
                self._check_and_compute()
            except Exception as e:
                logger.error(f"Compatibility worker error: {e}")
            
            # Wait before next check
            time.sleep(self.check_interval)
    
    def _process_queued_webhooks(self):
        """Check for queued webhooks and process them."""
        queue_file = os.path.join('data', 'webhook_queue.json')
        
        # Check if there's a queued webhook
        if not os.path.exists(queue_file):
            return
        
        try:
            # Load queue data
            with open(queue_file, 'r') as f:
                queue_data = json.load(f)
            
            sync_id = queue_data.get('sync_id')
            product_feed_url = queue_data.get('product_feed_url')
            
            if not sync_id or not product_feed_url:
                logger.error(f"Invalid queue data: {queue_data}")
                os.remove(queue_file)
                return
            
            logger.info(f"Processing queued webhook #{sync_id} from URL: {product_feed_url}")
            
            # Update sync status to processing
            from models import SyncStatus
            session = get_session()
            sync_record = session.query(SyncStatus).filter_by(id=sync_id).first()
            if not sync_record:
                logger.error(f"Sync record #{sync_id} not found!")
                session.close()
                return
            
            sync_record.status = 'processing'
            session.commit()
            session.close()
            
            # Process the webhook
            import requests
            import tempfile
            import shutil
            
            logger.info(f"Downloading Excel from Salsify S3: {product_feed_url}")
            
            response = requests.get(product_feed_url, timeout=300, stream=True)
            response.raise_for_status()
            
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 100 * 1024 * 1024:
                raise ValueError(f"File too large: {content_length} bytes (max 100MB)")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                downloaded_size = 0
                max_size = 100 * 1024 * 1024
                
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded_size += len(chunk)
                    if downloaded_size > max_size:
                        raise ValueError(f"Download exceeded max size: {max_size} bytes")
                    tmp_file.write(chunk)
                
                temp_path = tmp_file.name
                logger.info(f"Downloaded Excel file: {downloaded_size} bytes")
            
            # Save to main data directory
            main_excel_path = os.path.join('data', 'Product Data.xlsx')
            shutil.copy2(temp_path, main_excel_path)
            logger.info(f"Saved Excel file to: {main_excel_path}")
            
            # Sync database (WITHOUT computing compatibilities - too slow)
            import db_sync_service
            sync_result = db_sync_service.full_sync_workflow(temp_path, compute_compatibilities=False)
            
            # Reload in-memory cache
            try:
                import data_update_service
                data_update_service.load_data_into_memory(main_excel_path)
                logger.info("Reloaded in-memory cache with updated product data")
            except Exception as cache_error:
                logger.warning(f"Could not reload cache: {cache_error}")
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            # Update sync status
            session = get_session()
            sync_record = session.query(SyncStatus).filter_by(id=sync_id).first()
            
            if sync_result.get('success'):
                sync_record.status = 'completed'
                sync_record.completed_at = datetime.utcnow()
                sync_record.products_added = sync_result.get('products_added', 0)
                sync_record.products_updated = sync_result.get('products_updated', 0)
                sync_record.products_deleted = sync_result.get('products_deleted', 0)
                sync_record.compatibilities_updated = 0  # Will be computed separately
                
                # Store detailed change information
                from sqlalchemy.orm.attributes import flag_modified
                if sync_record.sync_metadata is None:
                    sync_record.sync_metadata = {}
                change_details = sync_result.get('change_details', {})
                sync_record.sync_metadata['change_details'] = change_details
                flag_modified(sync_record, 'sync_metadata')
                
                logger.info(f"Webhook #{sync_id} completed: {sync_record.products_added} added, {sync_record.products_updated} updated, {sync_record.products_deleted} deleted")
            else:
                sync_record.status = 'failed'
                sync_record.completed_at = datetime.utcnow()
                sync_record.error_message = sync_result.get('error', 'Unknown error')
                logger.error(f"Webhook #{sync_id} failed: {sync_result.get('error')}")
            
            # Commit database changes FIRST
            session.commit()
            session.close()
            
            # Only delete queue file AFTER successful database commit
            # This ensures crash during commit doesn't lose the webhook
            if os.path.exists(queue_file):
                os.remove(queue_file)
                logger.info(f"Removed queue file after database commit (status: {sync_record.status})")
            
        except Exception as e:
            logger.error(f"Error processing queued webhook: {e}")
            # Try to update sync status to failed
            try:
                from models import SyncStatus
                session = get_session()
                if 'sync_id' in locals():
                    sync_record = session.query(SyncStatus).filter_by(id=sync_id).first()
                    if sync_record:
                        sync_record.status = 'failed'
                        sync_record.error_message = str(e)
                        sync_record.completed_at = datetime.utcnow()
                        session.commit()  # Commit FIRST
                        
                        # Only delete queue file AFTER successful commit
                        if os.path.exists(queue_file):
                            os.remove(queue_file)
                            logger.info("Removed queue file after exception handling commit")
                session.close()
            except:
                # If we can't commit the failure, leave queue file for retry
                logger.error("Failed to commit error status - queue file retained for retry")
                pass
    
    def _cleanup_stuck_syncs(self):
        """On startup, fail any syncs stuck in 'processing' status from previous crashes."""
        try:
            from models import SyncStatus
            session = get_session()
            
            stuck_syncs = session.query(SyncStatus).filter(
                SyncStatus.status == 'processing'
            ).all()
            
            if stuck_syncs:
                logger.warning(f"Found {len(stuck_syncs)} syncs stuck in 'processing' - marking as failed")
                for sync in stuck_syncs:
                    sync.status = 'failed'
                    sync.completed_at = datetime.utcnow()
                    sync.error_message = 'Webhook processing interrupted by app restart. Compatibility worker now starts automatically to prevent this.'
                    logger.info(f"Marked sync #{sync.id} as failed")
                
                session.commit()
            
            session.close()
            logger.info("Startup cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during startup cleanup: {e}")
    
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
            
            # Don't recurse - let the main loop handle next batch to avoid blocking webhook processing
                
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
