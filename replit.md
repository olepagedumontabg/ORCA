# Bathroom Compatibility Finder

## Overview

The Bathroom Compatibility Finder is a Flask web application designed to identify compatible bathroom products (e.g., shower bases, bathtubs, doors, walls) by analyzing dimensional and specification data. It aims to streamline product selection for users and integrate with external applications.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
- **Frontend**: HTML templates styled with Tailwind CSS for a responsive, mobile-first design.
- **Interactivity**: Alpine.js for dynamic frontend elements.

### Technical Implementations
- **Backend**: Flask web application (Python 3.11) utilizing Pandas for Excel data manipulation.
- **Deployment**: Gunicorn WSGI server with autoscale deployment on Replit.
- **Data Update Service**: Automated, threaded service for FTP synchronization of product data, including scheduled daily updates and email notifications.
- **Core Logic**: Dedicated modules handle compatibility rules for various product types (shower, bathtub, tub shower, etc.), image URL generation, and compatibility overrides.
- **REST API**: Provides 5 endpoints for external integration, including health checks, category listings, product details, and compatibility queries.

### System Design Choices
- **Database-First**: PostgreSQL serves as the primary data source, supporting fast queries and multi-application access.
- **Hybrid Data Approach**: Utilizes both PostgreSQL for core operations and Excel files (`Product Data.xlsx`) for initial imports and web interface fallback.
- **Optimized Database Layer**:
    - SQLAlchemy ORM with connection pooling for efficient database interactions.
    - Pre-computed compatibility matches stored in `ProductCompatibility` table with composite indexes.
    - Intelligent data loader with query optimization, eager loading, and multi-SKU lookup.
    - Automated database synchronization (`db_sync_service.py`) with bulk operations and incremental updates for changes from Excel.
    - Incremental compatibility system (`incremental_compute.py`) for significantly faster product additions by processing only new products and using batch processing with pre-indexed lookups.

## Performance Metrics

### Current Performance (October 29, 2025)
- **API Response Times**:
    - Cached requests: **~4ms average** (97% faster than 100ms goal)
    - Uncached database queries: **~268ms average** (37% improvement from 416ms baseline)
    - First request cache warmup: ~300ms
- **Database Coverage**: 
    - **74.2%** of products (1,628/2,193) have forward compatibility
    - Remaining 565 products correctly have only reverse compatibility (doors, walls, screens as targets; incompatible bases/tubs)
    - **64,596 total compatibility records** (~32,298 bidirectional matches)
- **Database Optimization**:
    - Composite index `idx_base_score` on `(base_product_id, compatibility_score DESC)` for optimal sorted queries
    - Connection pooling with singleton engine pattern (saves 10-50ms per request)
    - Raw SQL queries for best performance on complex compatibility lookups
- **Test Results**: All tests passing
    - ✓ Database Coverage Test
    - ✓ Query Performance Test
    - ✓ API Caching Test

### Performance Testing
- **Tool**: `test_performance.py` - Automated performance test suite
- **Metrics**: Database coverage, query speed, API caching effectiveness
- **Results**: Consistently achieving sub-5ms cached responses

## External Dependencies

- **FTP Server**: Salsify.com for product data synchronization.
- **SendGrid**: Email notification service.
- **PostgreSQL**: Relational database.
- **Python Packages**:
    - Flask
    - Pandas
    - SQLAlchemy
    - psycopg2-binary
    - Gunicorn
    - SendGrid
    - Schedule
- **Frontend Libraries**: Alpine.js and Tailwind CSS (via CDN).