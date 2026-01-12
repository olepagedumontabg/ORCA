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
- **Data Update Service**: 
    - **Primary**: Salsify webhook integration for real-time automated updates (November 2025)
    - **Backup**: FTP synchronization service with scheduled daily updates and email notifications
- **Webhook Integration**: Secure webhook endpoint (`/api/salsify/webhook`) receives Salsify publication notifications, downloads Excel from S3, and triggers database sync with background processing.
- **Core Logic**: Dedicated modules handle compatibility rules for various product types (shower, bathtub, tub shower, etc.), image URL generation, and compatibility overrides.
- **REST API**: Provides 7 endpoints for external integration, including health checks, category listings, product details, compatibility queries, and Salsify webhook/status endpoints.

### System Design Choices
- **Single Production Database**: One PostgreSQL database (Neon-hosted) used by all environments - development, testing, and production deployment all share the same database via `DATABASE_URL`.
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

- **Salsify PIM**: Product Information Management system with webhook integration for automated data synchronization.
- **SendGrid**: Email notification service (optional).
- **PostgreSQL**: Relational database.
- **Python Packages**:
    - Flask
    - Pandas
    - SQLAlchemy
    - psycopg2-binary
    - Gunicorn
    - Requests (for S3 file downloads)
    - SendGrid (optional)
    - Schedule
- **Frontend Libraries**: Alpine.js and Tailwind CSS (via CDN).

## Recent Updates (November 2025)

### Salsify Webhook Integration
- **Implemented**: Full webhook integration with Salsify PIM system
- **Endpoints Added**: 
    - `POST /api/salsify/webhook` - Receives publication notifications
    - `GET /api/salsify/status` - Monitors sync operations
- **Features**:
    - URL-based authentication using `SALSIFY_WEBHOOK_SECRET`
    - Background processing with threading (non-blocking 202 response)
    - S3 file download with 100MB limit and 5-minute timeout
    - Automatic database sync and compatibility recomputation
    - Saves downloaded Excel to `data/Product Data.xlsx` and reloads in-memory cache
    - Comprehensive sync status tracking in `sync_status` table
- **Security**: Secret stored in Replit Secrets, file size/timeout protections
- **Testing**: Comprehensive test suite in `test_webhook.py`
- **Documentation**: Full setup guide in `SALSIFY_WEBHOOK_SETUP.md`

### Webhook Reliability Fixes (January 12, 2026)
- **Problem**: Webhooks getting stuck in "processing" status indefinitely, plus SQLAlchemy session errors
- **Root Cause**: Multiple bugs in compatibility worker (`compatibility_worker.py`)
- **Fixes Implemented**:
    1. **Queue File Deletion Timing**:
        - **Before**: Queue file deleted BEFORE database commit → Lost webhooks on crash
        - **After**: Queue file deleted ONLY AFTER successful commit → Webhooks survive crashes
        - **Impact**: Eliminates webhook loss during app restarts or commit failures
    2. **Compatibility Batch Processing**:
        - **Before**: Recursive batching blocked main loop for >5 minutes
        - **After**: Non-recursive - processes one batch per 2-minute cycle
        - **Impact**: Webhooks checked every 2 minutes, meeting 3-5 minute target
    3. **Startup Cleanup**:
        - **Before**: Stuck syncs from crashes remained in "processing" forever
        - **After**: Automatic cleanup on startup fails orphaned syncs
        - **Impact**: Clean recovery from app crashes/restarts
    4. **SQLAlchemy Detached Instance Fix** (January 2026):
        - **Before**: Accessing `sync_record.status` after session closed caused "Instance not bound to Session" error
        - **After**: Store status in local variable before closing session
        - **Impact**: Eliminates SQLAlchemy detached instance errors during webhook completion
- **Result**: Webhooks now reliably process within 3-5 minutes without getting stuck or throwing session errors
- **Worker Status**: Automatic compatibility worker starts on app initialization and stays running

### Compatibility Override Columns (November 4, 2025)
- **Feature**: Support for forced compatibility via Salsify columns
- **Columns**:
    - `Compatible Doors` - Force specific door SKUs to appear as compatible
    - `Compatible Walls` - Force specific wall SKUs to appear as compatible
- **Behavior**:
    - Override products are merged with normally matched products (not just fallback)
    - Duplicates are automatically removed by SKU
    - Products maintain ranking order after merge
    - Supports both comma-separated (`SKU1, SKU2`) and pipe-separated (`SKU1|SKU2`) formats
- **Use Case**: Bypass normal compatibility logic to force specific product pairings

### Database Consolidation (November 5, 2025)
- **Architecture Change**: Consolidated from separate dev/prod databases to single production database
- **Simplification**: All environments (development, testing, production) now use the same database
- **Configuration**: `DATABASE_URL` points to production Neon database
- **Benefits**: Eliminated sync confusion, single source of truth, simplified debugging
- **Removed**: Obsolete dev-to-prod sync scripts (`sync_to_production.py`, `copy_dev_to_prod.py`, `lightning_sync.py`)