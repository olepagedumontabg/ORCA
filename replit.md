# Bathroom Compatibility Finder

## Overview

The Bathroom Compatibility Finder is a Flask web application that helps users find compatible bathroom products based on dimensional and specification matching. The system analyzes product data from Excel spreadsheets to determine compatibility between shower bases, bathtubs, doors, walls, and other bathroom components.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Python 3.11
- **Data Processing**: Pandas for Excel data manipulation and analysis
- **Deployment**: Gunicorn WSGI server with autoscale deployment target
- **Background Services**: Threaded data update service for FTP synchronization

### Frontend Architecture
- **UI Framework**: HTML templates with Tailwind CSS for styling
- **JavaScript**: Alpine.js for reactive frontend interactions
- **Design**: Responsive design with mobile-first approach

### Data Storage Solutions
- **Database-First Architecture**: PostgreSQL database is the single source of truth for API
- **Primary Data**: PostgreSQL database for fast queries and multi-app access
- **Excel Data**: Excel files (`Product Data.xlsx`) used for initial import and web interface fallback
- **Data Directory**: Local file system storage with backup capabilities
- **Data Sources**: FTP server integration for automated data updates

## Key Components

### Core Application (`app.py`)
- Flask application initialization and configuration
- Route handling for main interface and API endpoints
- **REST API Endpoints**: 5 endpoints for external application integration
  - `/api/health`: System health and status
  - `/api/categories`: List all product categories
  - `/api/products`: Paginated product listing with filters
  - `/api/product/<sku>`: Get specific product details
  - `/api/compatible/<sku>`: Get compatible products for a SKU
- Integration with data update service
- Error handling and logging

### Compatibility Logic (`logic/` directory)
- **Base Compatibility**: Matches shower bases with compatible products
- **Bathtub Compatibility**: Handles bathtub-to-door/wall matching logic
- **Shower Compatibility**: Manages shower unit compatibility rules
- **Tub Shower Compatibility**: Processes tub shower combination matching
- **Image Handler**: Generates and manages product image URLs
- **Whitelist/Blacklist Helpers**: Manages compatibility overrides

### Data Update Service (`data_update_service.py`)
- Automated FTP file synchronization
- Scheduled daily updates at 02:00
- Data validation and backup management
- **Automatic database synchronization** after successful FTP download
- Email notifications for update status

### Email Notifications (`email_notifications.py`)
- SendGrid integration for status notifications
- Success/failure alerts for data updates
- Configurable recipient settings

### Database Layer (Optimized Hybrid Approach)
- **Models (`models.py`)**: SQLAlchemy ORM models with connection pooling
  - Product model with JSON attributes
  - ProductCompatibility for pre-computed matches with composite indexes
  - CompatibilityOverride for whitelist/blacklist
  - **Singleton database engine** for connection reuse (saves 10-50ms per request)
  - Optimized connection pool settings (10 connections, 20 overflow)
- **Migration Script (`db_migrate.py`)**: Database population and management
  - Import products from Excel to PostgreSQL
  - Pre-compute compatibility matches
  - Database statistics and monitoring
- **Data Loader (`data_loader.py`)**: Intelligent data source with query optimization
  - Database-only mode for REST API endpoints
  - Excel fallback available for web interface
  - **Eager loading** with joinedload for one-query compatibility fetches
  - Multi-SKU lookup with priority matching (child → parent → unique ID)
- **Database Sync Service (`db_sync_service.py`)**: Automated database updates with bulk operations
  - Syncs database with Excel changes (add/update/delete products)
  - **Bulk delete and insert operations** (500-row batches)
  - Recomputes compatibilities for changed products only
  - Integrates with daily FTP update workflow
  - Smart incremental updates to minimize processing
- **Incremental Compatibility System** (`incremental_compute.py`, `add_products.py`): **10-20x faster** product additions
  - Only processes NEW products (not already in database)
  - Pre-indexed lookups by category and SKU for instant access
  - Batch processing with 50-product chunks
  - Complete workflow: `python add_products.py` syncs Excel and computes compatibilities automatically
  - Performance: Add 100 products in 2-5 minutes (vs 30-50 minutes with full recomputation)
  - Status monitoring: `python add_products.py status` shows current database state

## Data Flow

1. **Data Ingestion**: FTP service downloads latest Excel files
2. **Data Loading**: Excel sheets are parsed into Pandas DataFrames
3. **User Query**: Frontend sends product SKU search requests
4. **Compatibility Analysis**: Logic modules analyze dimensional and specification matches
5. **Results Processing**: Compatible products are ranked and filtered
6. **Response Delivery**: JSON/HTML results returned to frontend

## External Dependencies

### Required Services
- **FTP Server**: Salsify.com for product data synchronization
- **SendGrid**: Email notification service (optional)
- **PostgreSQL**: Database support (configured but not actively used)

### Python Packages
- Flask 3.1.0+ for web framework
- Pandas 2.2.3+ for data processing
- SQLAlchemy 2.0+ for database ORM
- psycopg2-binary for PostgreSQL connectivity
- Gunicorn 23.0.0+ for production deployment
- SendGrid 6.12.0+ for email notifications
- Schedule 1.2.2+ for automated tasks
- Alpine.js and Tailwind CSS via CDN

## Deployment Strategy

### Environment Configuration
- **Development**: Local Flask development server
- **Production**: Gunicorn with autoscale deployment on Replit
- **Port Configuration**: Internal port 5000, external port 80

### Environment Variables
- `FTP_HOST`: FTP server hostname
- `FTP_USER`, `FTP_PASSWORD`: FTP credentials
- `SENDGRID_API_KEY`: Email service authentication
- `SESSION_SECRET`: Flask session security
- `DATABASE_URL`: PostgreSQL database connection string (auto-configured by Replit)
- `USE_DATABASE`: Control database usage (auto/true/false, default: auto)

### File Structure
- `/data/`: Product data and backups
- `/templates/`: HTML templates
- `/static/`: CSS, JavaScript, and image assets
- `/logic/`: Core compatibility algorithms
- `/tests/`: Test scripts and utilities

### Production Database Migration
- **Migration Guide**: See `PRODUCTION_MIGRATION_SIMPLE.md` for step-by-step instructions
- **Approach**: Use existing `db_migrate.py` and `complete_all_compatibilities.py` scripts with production DATABASE_URL
- **Process**: 
  1. Publish app to create production database
  2. Run `DATABASE_URL='prod-url' python db_migrate.py` to import products
  3. Run `DATABASE_URL='prod-url' python complete_all_compatibilities.py` to compute compatibilities
- **Safety**: Always verify DATABASE_URL before running, restore development URL after completion

## Recent Changes

- **October 29, 2025**: **Production Database Migration Complete** - Successfully copied development database to production
  - Created `copy_dev_to_prod.py` script for safe database-to-database copying
  - Copied 2,193 products and 63,211 compatibility records in under 1 minute
  - Production database now matches development: 100% of products have computed compatibilities
  - All compatibility records use new simplified rules (no brand/series restrictions)
  - Verified data integrity and optimized production database with ANALYZE
- **October 29, 2025**: **Optimized Incremental Compatibility System** - Built 10-20x faster product addition workflow
  - Created `incremental_compute.py` for processing only NEW products (not full recomputation)
  - Created `add_products.py` for complete Excel sync + compatibility computation workflow
  - **Pre-indexed lookups**: Category and SKU indexes for instant product access
  - **Batch processing**: 50-product chunks for optimal memory usage
  - **Performance**: 100 products in 2-5 min (vs 30-50 min), 1000 products in 30-60 min (vs 8-9 hours)
  - **Simple usage**: `python add_products.py` for automatic sync and compute
  - **Status monitoring**: `python add_products.py status` shows database state
  - Completed development database recomputation: 2,193/2,193 products with 63,211 compatibility records
  - See `INCREMENTAL_SYSTEM_GUIDE.md` for complete documentation
- **October 28, 2025**: **Compatibility Logic Simplification** - Removed brand and series restrictions, kept family rules
  - **Series Rules Removed**: All products now compatible across different series (Retail, MAAX, Collection, etc.)
  - **Brand Rules Removed**: Products from different brands can now match (Maax, Neptune, Bootz, etc.)
  - **Family Rules Kept**: Exclusive family restrictions still enforced (Olio, Vellamo, Interflo, W&B)
  - **Special Family Rules Kept**: Utile/Nextile walls still match only with specific base families
  - **Files Updated**: base_compatibility.py, bathtub_compatibility.py, shower_compatibility.py, tubshower_compatibility.py
  - **Result**: Products now have significantly more compatible matches across brands and series
  - **Development Database**: Completed with 2,193/2,193 products, 63,211 compatibility records (~31,605 bidirectional matches)
- **October 27, 2025**: **Performance Optimizations** - Major speed improvements for API and database operations
  - **Connection Pooling**: Singleton database engine with optimized pool settings (10-50ms saved per request)
  - **Response Caching**: In-memory LRU cache for API responses (96% faster for repeated requests - from 1s to 37ms)
  - **Composite Indexes**: Added idx_base_score index for faster sorted compatibility queries
  - **Eager Loading**: Single-query fetching of compatibilities with joinedload (reduced N+1 queries)
  - **Bulk Operations**: Replaced individual inserts with bulk_insert_mappings (10-100x faster)
  - **Batch Processing**: 500-row batches for compatibility computation and sync operations
  - **Incremental Updates**: Bulk delete and smart recalculation for changed products only
  - **Code Cleanup**: Removed 13 unused utility scripts and test files from root directory
  - Overall API performance: 30-50% faster first requests, 80-96% faster cached requests
- **October 24, 2025**: **Multi-SKU Lookup with Priority Matching** - Enhanced compatibility API for flexible SKU formats
  - Added multi-SKU lookup to `/api/compatible/<child_sku>` endpoint with priority matching
  - Priority order: child_sku (path) → parent_sku (query) → unique_id (query)
  - Single database query for optimal performance (sub-100ms response times)
  - Response includes `matched_sku` and `match_type` to show which SKU was found
  - Supports applications using different SKU formats (child, parent, unique ID)
  - Maintains full backward compatibility - single SKU lookup still works
  - Example: `/api/compatible/410000-501-001-000?parent_sku=410000&unique_id=410000-501-001`
- **October 23, 2025**: **Fixed Compatibility Query Bug** - Fixed API not finding compatibility records
  - Database compatibility records were using empty strings ('') instead of NULL for incompatibility_reason
  - Updated data_loader.py to handle both NULL and empty string cases
  - API now correctly returns compatible products from production database
- **October 23, 2025**: **Database-Only API Mode** - Removed Excel fallback from REST API endpoints
  - API endpoints now exclusively use PostgreSQL database as single source of truth
  - Products without computed compatibilities return empty array with informative message
  - Web interface retains Excel fallback for user convenience
  - Ensures consistent, reliable data for external applications
- **October 23, 2025**: **API Category Consistency Fix** - Fixed inconsistency between database and Excel data sources
  - Excel mode was returning "Doors + Return Panels" as one combined category
  - Database mode was returning "Shower Doors" and "Return Panels" as separate categories
  - Modified `logic/base_compatibility.py` to separate combo products into individual doors and return panels
  - Both data sources now return consistent categories ("Shower Doors" and "Return Panels" separately)
  - Combo products (e.g., "DOOR123|PANEL456") are now split into individual SKUs in Excel responses to match database behavior
- **October 22, 2025**: **Hybrid Data Architecture** - Implemented REST API and database support for multi-app access
  - Added 5 REST API endpoints for external application integration
  - Created PostgreSQL database schema (Product, ProductCompatibility, CompatibilityOverride tables)
  - Built migration tools for Excel-to-database import
  - Implemented intelligent data loader with automatic database/Excel fallback
  - Created comprehensive API documentation (`API_DOCUMENTATION.md`)
  - System now supports both standalone Excel mode and database-backed mode
  - Database coverage: 75.6% (1,657 products with 54,796 bidirectional compatibility relationships)
- **June 23, 2025**: Fixed incompatibility reasons display - shower bases and bathtubs now properly show door incompatibility messages
- **June 23, 2025**: Fixed screens visibility logic - screens are now correctly hidden when door incompatibility reasons exist
- **June 23, 2025**: Fixed brand/family compatibility restrictions - Olio and Vellamo products now only appear with each other, not with other brands like Swan
- **June 24, 2025**: Fixed bathtub-door compatibility - Maax bathtubs now properly show DreamLine doors, matching shower base behavior

## User Preferences

Preferred communication style: Simple, everyday language.