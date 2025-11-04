import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DECIMAL, TIMESTAMP, Boolean, Index, ForeignKey, UniqueConstraint, JSON, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine instance for connection pooling
_engine = None
_engine_lock = None


class Product(Base):
    """
    Product model representing all bathroom products across all categories.
    """
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    product_name = Column(Text)
    brand = Column(String(100), index=True)
    series = Column(String(100), index=True)
    family = Column(String(100), index=True)
    category = Column(String(50), nullable=False, index=True)
    
    length = Column(DECIMAL(10, 2))
    width = Column(DECIMAL(10, 2))
    height = Column(DECIMAL(10, 2))
    nominal_dimensions = Column(String(50))
    
    attributes = Column(JSON)
    
    product_page_url = Column(Text)
    image_url = Column(Text)
    
    ranking = Column(Integer)
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    compatibilities_from = relationship(
        'ProductCompatibility',
        foreign_keys='ProductCompatibility.base_product_id',
        back_populates='base_product',
        cascade='all, delete-orphan'
    )
    
    compatibilities_to = relationship(
        'ProductCompatibility',
        foreign_keys='ProductCompatibility.compatible_product_id',
        back_populates='compatible_product',
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f"<Product(sku='{self.sku}', name='{self.product_name}', category='{self.category}')>"


class ProductCompatibility(Base):
    """
    Product compatibility model storing pre-computed compatibility matches.
    """
    __tablename__ = 'product_compatibility'
    
    id = Column(Integer, primary_key=True)
    base_product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    compatible_product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    
    compatibility_score = Column(Integer)
    match_reason = Column(Text)
    incompatibility_reason = Column(Text)
    
    computed_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    base_product = relationship('Product', foreign_keys=[base_product_id], back_populates='compatibilities_from')
    compatible_product = relationship('Product', foreign_keys=[compatible_product_id], back_populates='compatibilities_to')
    
    __table_args__ = (
        UniqueConstraint('base_product_id', 'compatible_product_id', name='uq_product_compatibility'),
        Index('idx_compatibility_base', 'base_product_id'),
        Index('idx_compatibility_compatible', 'compatible_product_id'),
        Index('idx_compatibility_score', 'compatibility_score'),
        # Composite index for ordered compatibility lookups (critical for API performance)
        # DESC ordering ensures highest scores first without reverse scan
        Index('idx_base_score', 'base_product_id', desc('compatibility_score')),
    )
    
    def __repr__(self):
        return f"<ProductCompatibility(base_id={self.base_product_id}, compatible_id={self.compatible_product_id}, score={self.compatibility_score})>"


class CompatibilityOverride(Base):
    """
    Compatibility override model for whitelist/blacklist management.
    """
    __tablename__ = 'compatibility_overrides'
    
    id = Column(Integer, primary_key=True)
    base_sku = Column(String(50), nullable=False, index=True)
    compatible_sku = Column(String(50), nullable=False, index=True)
    override_type = Column(String(20), nullable=False)
    reason = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('base_sku', 'compatible_sku', 'override_type', name='uq_compatibility_override'),
    )
    
    def __repr__(self):
        return f"<CompatibilityOverride(base='{self.base_sku}', compatible='{self.compatible_sku}', type='{self.override_type}')>"


class SyncStatus(Base):
    """
    Sync status model for tracking webhook and automated sync operations.
    """
    __tablename__ = 'sync_status'
    
    id = Column(Integer, primary_key=True)
    sync_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    completed_at = Column(TIMESTAMP)
    
    products_added = Column(Integer, default=0)
    products_updated = Column(Integer, default=0)
    products_deleted = Column(Integer, default=0)
    compatibilities_updated = Column(Integer, default=0)
    
    error_message = Column(Text)
    sync_metadata = Column(JSON)
    
    __table_args__ = (
        Index('idx_sync_status_type', 'sync_type'),
        Index('idx_sync_status_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<SyncStatus(type='{self.sync_type}', status='{self.status}', started='{self.started_at}')>"


def get_engine():
    """
    Get or create a singleton database engine with connection pooling.
    This reuses the same engine across requests for better performance.
    """
    global _engine, _engine_lock
    
    if _engine is not None:
        return _engine
    
    # Thread-safe engine creation
    import threading
    if _engine_lock is None:
        _engine_lock = threading.Lock()
    
    with _engine_lock:
        # Double-check pattern
        if _engine is not None:
            return _engine
        
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Create engine with optimized pooling settings
        _engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            poolclass=QueuePool,
            pool_size=10,           # Maintain 10 connections
            max_overflow=20,        # Allow up to 30 total connections
            pool_recycle=3600,      # Recycle connections after 1 hour
            pool_timeout=30,        # Wait up to 30 seconds for connection
        )
        logger.info("Database engine created with connection pooling")
        return _engine


def get_session():
    """
    Create and return a database session.
    """
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def create_tables():
    """
    Create all database tables defined in the models.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """
    Drop all database tables. Use with caution!
    """
    engine = get_engine()
    Base.metadata.drop_all(engine)
    logger.warning("Database tables dropped")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Done!")
