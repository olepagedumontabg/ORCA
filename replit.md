# Bathroom Compatibility Finder — API

## Overview

A lean Flask REST API that identifies compatible bathroom products (shower bases, bathtubs, doors, walls) by analyzing dimensional and specification data. Consumed by an external ASP.NET front-end via the ORCA.API endpoints.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Technical Implementations
- **Backend**: Flask API (Python 3.11) utilizing Pandas for Excel data manipulation and SQLAlchemy for database access.
- **Deployment**: Gunicorn WSGI server with autoscale deployment on Replit.
- **Data Update**:
    - **Primary**: Salsify webhook integration for real-time automated updates — `/api/salsify/webhook` receives publication notifications, downloads Excel from S3, and triggers a background database sync.
- **Core Logic**: Dedicated modules handle compatibility rules for various product types (shower, bathtub, tub shower, etc.), image URL generation, and compatibility overrides.
- **REST API**: 9 endpoints — health check, category listing, product details, compatibility queries, Salsify webhook/status/cleanup, and a manual compute-compatibilities trigger.

### System Design Choices
- **Single Production Database**: One PostgreSQL database (Neon-hosted) shared across all environments via `DATABASE_URL`.
- **Hybrid Data Approach**: PostgreSQL for live queries; Excel files (`Product Data.xlsx`) for initial imports and re-sync.
- **Optimized Database Layer**:
    - SQLAlchemy ORM with connection pooling.
    - Pre-computed compatibility matches stored in `ProductCompatibility` table with composite indexes.
    - Intelligent data loader with query optimization, eager loading, and multi-SKU lookup.
    - Automated database sync (`db_sync_service.py`) with bulk operations and incremental updates.
- **In-memory API cache**: Simple LRU-style dict cache (1000 entries) invalidated after each data sync.

### Project Structure
- **`logic/`** - Core compatibility engine with shared business rules
- **`services/`** - Backend services: `data_loader.py`, `db_sync_service.py`, `compatibility_worker.py`, `json_utils.py`
- **`data/`** - Excel data files and backups

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + DB stats |
| GET | `/api/categories` | All product categories |
| GET | `/api/products` | All products (optional `?category=`) |
| GET | `/api/product/<sku>` | Single product details |
| GET | `/api/compatible/<sku>` | Compatible products for a SKU |
| POST | `/api/compute-compatibilities` | Trigger compatibility recompute |
| POST | `/api/salsify/webhook` | Salsify publication webhook |
| GET | `/api/salsify/status` | Last sync status |
| POST | `/api/salsify/cleanup` | Clean up stale sync records |

## External Dependencies

- **Salsify PIM**: Product Information Management system — webhook integration for automated data sync.
- **PostgreSQL**: Relational database (Neon-hosted).
- **Python Packages**:
    - Flask
    - Pandas
    - SQLAlchemy
    - psycopg2-binary
    - Gunicorn
    - Requests (for S3 file downloads)
