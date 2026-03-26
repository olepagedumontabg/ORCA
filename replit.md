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

### Project Structure
- **`logic/`** - Core compatibility engine with shared business rules
- **`services/`** - Backend services (data loader, sync, worker, email)
- **`templates/`** - Frontend HTML templates
- **`static/`** - Frontend assets (CSS, JS, images)
- **`data/`** - Excel data files and backups
- **`tests/`** - Unit tests

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
