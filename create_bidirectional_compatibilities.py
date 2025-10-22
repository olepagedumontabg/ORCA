"""
Create bidirectional compatibility relationships.

For every compatibility A→B, create the reverse B→A so that
searching from either product finds the other.

Example:
- If Shower Base → Door exists, create Door → Shower Base
- If Shower Base → Wall exists, create Wall → Shower Base
"""

import logging
from models import get_session, ProductCompatibility

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_reverse_compatibilities():
    """
    Create reverse compatibility relationships for all existing compatibilities.
    """
    session = get_session()
    
    try:
        # Get all existing compatibilities
        existing_compatibilities = session.query(ProductCompatibility).all()
        total_existing = len(existing_compatibilities)
        
        logger.info(f"Found {total_existing} existing compatibility relationships")
        logger.info("Creating reverse relationships...")
        
        # Track what we've already created to avoid duplicates
        existing_pairs = set()
        for compat in existing_compatibilities:
            existing_pairs.add((compat.base_product_id, compat.compatible_product_id))
        
        logger.info(f"Existing pairs tracked: {len(existing_pairs)}")
        
        # Create reverse relationships
        reverse_count = 0
        duplicate_count = 0
        
        for compat in existing_compatibilities:
            # Check if reverse already exists
            reverse_pair = (compat.compatible_product_id, compat.base_product_id)
            
            if reverse_pair in existing_pairs:
                duplicate_count += 1
                continue
            
            # Create reverse relationship
            reverse_compat = ProductCompatibility(
                base_product_id=compat.compatible_product_id,
                compatible_product_id=compat.base_product_id,
                compatibility_score=compat.compatibility_score,
                match_reason=f"Reverse: {compat.match_reason}",
                incompatibility_reason=compat.incompatibility_reason
            )
            session.add(reverse_compat)
            existing_pairs.add(reverse_pair)
            reverse_count += 1
            
            # Commit in batches
            if reverse_count % 100 == 0:
                session.commit()
                logger.info(f"Progress: {reverse_count} reverse relationships created")
        
        # Final commit
        session.commit()
        
        logger.info("=" * 80)
        logger.info("BIDIRECTIONAL COMPATIBILITY CREATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Original compatibilities: {total_existing}")
        logger.info(f"Reverse compatibilities created: {reverse_count}")
        logger.info(f"Duplicates skipped: {duplicate_count}")
        logger.info(f"Total compatibilities now: {total_existing + reverse_count}")
        logger.info("=" * 80)
        
        return reverse_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating reverse compatibilities: {str(e)}")
        raise
    finally:
        session.close()


def verify_bidirectional():
    """
    Verify that bidirectional relationships exist.
    """
    session = get_session()
    
    try:
        from sqlalchemy import func, and_
        
        # Count total compatibilities
        total = session.query(ProductCompatibility).count()
        
        # Sample check: for random compatibility A→B, check if B→A exists
        sample_compat = session.query(ProductCompatibility).first()
        
        if sample_compat:
            reverse_exists = session.query(ProductCompatibility).filter(
                and_(
                    ProductCompatibility.base_product_id == sample_compat.compatible_product_id,
                    ProductCompatibility.compatible_product_id == sample_compat.base_product_id
                )
            ).first()
            
            logger.info(f"Sample verification:")
            logger.info(f"  Original: Product {sample_compat.base_product_id} → Product {sample_compat.compatible_product_id}")
            logger.info(f"  Reverse exists: {'✓ YES' if reverse_exists else '✗ NO'}")
        
        logger.info(f"Total bidirectional compatibilities: {total}")
        
    finally:
        session.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Create bidirectional compatibilities')
    parser.add_argument('--verify', action='store_true', help='Verify bidirectional relationships exist')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_bidirectional()
    else:
        create_reverse_compatibilities()
        verify_bidirectional()
