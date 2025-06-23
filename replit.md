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
- **Primary Data**: Excel files (`Product Data.xlsx`) containing product catalogs
- **Data Directory**: Local file system storage with backup capabilities
- **Data Sources**: FTP server integration for automated data updates

## Key Components

### Core Application (`app.py`)
- Flask application initialization and configuration
- Route handling for main interface and API endpoints
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
- Email notifications for update status

### Email Notifications (`email_notifications.py`)
- SendGrid integration for status notifications
- Success/failure alerts for data updates
- Configurable recipient settings

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

### File Structure
- `/data/`: Product data and backups
- `/templates/`: HTML templates
- `/static/`: CSS, JavaScript, and image assets
- `/logic/`: Core compatibility algorithms
- `/tests/`: Test scripts and utilities

## Recent Changes

- **June 23, 2025**: Fixed incompatibility reasons display - shower bases and bathtubs now properly show door incompatibility messages
- **June 23, 2025**: Fixed screens visibility logic - screens are now correctly hidden when door incompatibility reasons exist
- **June 23, 2025**: Fixed brand/family compatibility restrictions - Olio and Vellamo products now only appear with each other, not with other brands like Swan

## User Preferences

Preferred communication style: Simple, everyday language.