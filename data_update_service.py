"""
Data Update Service for Bathroom Compatibility Finder

This service connects to an FTP server, downloads the latest Excel file,
validates it, and loads it into the application memory without disruption.
"""

import os
import time
import logging
import shutil
import threading
import pandas as pd
import schedule
import ftplib
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_update.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("data_update_service")

# Configuration
class Config:
    # FTP Settings
    FTP_HOST = os.environ.get('FTP_SERVER', '') # Using FTP_SERVER as the environment variable name
    FTP_USER = os.environ.get('FTP_USER', '')
    FTP_PASSWORD = os.environ.get('FTP_PASSWORD', '')
    FTP_PATH = os.environ.get('FTP_PATH', '/')
    FTP_FILENAME_PREFIX = 'Product Data' # Files will be prefixed with this and have date suffixes
    
    # Local paths
    DATA_DIR = Path('data')
    BACKUP_DIR = DATA_DIR / 'backup'
    CURRENT_FILE = DATA_DIR / 'Product Data.xlsx'
    TEMP_FILE = DATA_DIR / 'temp_product_data.xlsx'
    
    # Default filename for local use
    DEFAULT_FILENAME = 'Product Data.xlsx'
    
    # Update schedule (24-hour format, e.g., "02:00" for 2 AM)
    UPDATE_TIME = os.environ.get('UPDATE_TIME', '02:00')
    
    # Number of backup files to keep
    MAX_BACKUPS = int(os.environ.get('MAX_BACKUPS', '7'))

# Global variable to hold the data
product_data_cache = {}
last_update_time = None
data_lock = threading.RLock()

def ensure_directories():
    """Ensure necessary directories exist"""
    Config.DATA_DIR.mkdir(exist_ok=True)
    Config.BACKUP_DIR.mkdir(exist_ok=True)
    logger.info(f"Ensured data directories exist: {Config.DATA_DIR}, {Config.BACKUP_DIR}")

def download_from_ftp():
    """Download the latest file from FTP server that matches the prefix and has the most recent date suffix"""
    if not all([Config.FTP_HOST, Config.FTP_USER, Config.FTP_PASSWORD]):
        logger.error("FTP credentials not provided. Set FTP_SERVER, FTP_USER, and FTP_PASSWORD environment variables.")
        return False
    
    try:
        logger.info(f"Connecting to FTP server {Config.FTP_HOST}")
        with ftplib.FTP(Config.FTP_HOST) as ftp:
            ftp.login(Config.FTP_USER, Config.FTP_PASSWORD)
            
            # Change to the specified directory
            if Config.FTP_PATH != '/':
                ftp.cwd(Config.FTP_PATH)
            
            # Get list of all files in the directory
            file_list = ftp.nlst()
            
            # Filter files that start with the prefix
            matching_files = [f for f in file_list if f.startswith(Config.FTP_FILENAME_PREFIX)]
            
            if not matching_files:
                logger.error(f"No files with prefix '{Config.FTP_FILENAME_PREFIX}' found on FTP server")
                return False
            
            # Sort files by name (assuming date suffix makes newer files sort later)
            # This should work for most date formats YYYYMMDD, etc.
            matching_files.sort(reverse=True)
            
            # Select the newest file (first after sorting in reverse)
            newest_file = matching_files[0]
            
            logger.info(f"Found newest file: {newest_file}")
            
            # Download file
            logger.info(f"Downloading {newest_file} to {Config.TEMP_FILE}")
            with open(Config.TEMP_FILE, 'wb') as f:
                ftp.retrbinary(f'RETR {newest_file}', f.write)
            
            logger.info("File downloaded successfully")
            return True
    except Exception as e:
        logger.error(f"Error downloading file from FTP: {str(e)}")
        return False

def validate_excel_file(file_path):
    """Validate that the Excel file has the expected structure"""
    try:
        logger.info(f"Validating Excel file: {file_path}")
        
        # Try to read the Excel file
        xls = pd.ExcelFile(file_path)
        
        # Check for at least some required worksheets
        # All files should have at least these sheets
        critical_sheets = ['Shower Bases']
        missing_critical_sheets = [sheet for sheet in critical_sheets if sheet not in xls.sheet_names]
        
        if missing_critical_sheets:
            logger.error(f"Excel file missing critical sheets: {', '.join(missing_critical_sheets)}")
            return False
        
        # These are the common sheets we expect to see
        expected_sheets = ['Shower Bases', 'Shower Doors', 'Return Panels', 'Walls', 'Enclosures']
        missing_expected_sheets = [sheet for sheet in expected_sheets if sheet not in xls.sheet_names]
        
        if missing_expected_sheets:
            logger.warning(f"Excel file missing some expected sheets: {', '.join(missing_expected_sheets)}")
            # Continue validation with the sheets that are present
        
        # Check each worksheet for minimum required columns
        # Every sheet should at least have these columns
        basic_required_columns = ['Unique ID', 'Product Name']
        
        # Additional required columns per sheet type
        sheet_specific_columns = {
            'Shower Bases': ['Nominal Dimensions'],
            # Make Min/Max Width optional for Shower Doors since they might be named differently
            'Shower Doors': [],
            'Return Panels': [],
            'Walls': ['Nominal Dimensions'],
            'Enclosures': ['Nominal Dimensions']
        }
        
        # Process only sheets that are present in the file
        for sheet in [s for s in expected_sheets if s in xls.sheet_names]:
            df = pd.read_excel(file_path, sheet_name=sheet)
            
            # Check for basic columns that every sheet should have
            missing_basic_columns = [col for col in basic_required_columns if col not in df.columns]
            
            if missing_basic_columns:
                logger.error(f"Sheet {sheet} missing basic required columns: {', '.join(missing_basic_columns)}")
                return False
            
            # Check for sheet-specific columns if defined
            if sheet in sheet_specific_columns:
                missing_specific_columns = [col for col in sheet_specific_columns[sheet] if col not in df.columns]
                
                if missing_specific_columns:
                    logger.warning(f"Sheet {sheet} missing some sheet-specific columns: {', '.join(missing_specific_columns)}")
                    # Continue validation - this is a warning, not a fatal error
        
        logger.info("Excel file validated successfully")
        return True
    except Exception as e:
        logger.error(f"Error validating Excel file: {str(e)}")
        return False

def backup_current_file():
    """Create a backup of the current data file"""
    if not Config.CURRENT_FILE.exists():
        logger.warning("No current file to backup")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = Config.BACKUP_DIR / f"Product_Data_{timestamp}.xlsx"
    
    try:
        logger.info(f"Creating backup: {backup_file}")
        shutil.copy2(Config.CURRENT_FILE, backup_file)
        
        # Clean up old backups if necessary
        cleanup_old_backups()
        
        logger.info("Backup created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return False

def cleanup_old_backups():
    """Remove old backup files, keeping only the most recent ones"""
    try:
        backup_files = sorted(list(Config.BACKUP_DIR.glob("Product_Data_*.xlsx")))
        
        # If we have more than MAX_BACKUPS, delete the oldest ones
        if len(backup_files) > Config.MAX_BACKUPS:
            for old_file in backup_files[:-Config.MAX_BACKUPS]:
                logger.info(f"Removing old backup: {old_file}")
                old_file.unlink()
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {str(e)}")

def load_data_into_memory(file_path):
    """Load the Excel data into memory"""
    global product_data_cache, last_update_time
    
    try:
        logger.info(f"Loading data from {file_path} into memory")
        
        with data_lock:
            # Read all sheets from the Excel file
            xls = pd.ExcelFile(file_path)
            
            # Create a new data cache
            new_data_cache = {}
            
            # Load each sheet into the cache
            for sheet_name in xls.sheet_names:
                logger.info(f"Loading sheet: {sheet_name}")
                new_data_cache[sheet_name] = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Update the global cache with the new data
            product_data_cache = new_data_cache
            last_update_time = datetime.now()
            
            logger.info(f"Data loaded successfully. {len(new_data_cache)} sheets loaded.")
            return True
    except Exception as e:
        logger.error(f"Error loading data into memory: {str(e)}")
        return False

def get_product_data():
    """Thread-safe function to access the product data cache"""
    with data_lock:
        return product_data_cache.copy(), last_update_time

def update_data():
    """Main function to update the data"""
    logger.info("Starting data update process")
    
    # Ensure directories exist
    ensure_directories()
    
    # Download the file from FTP
    if not download_from_ftp():
        logger.error("Failed to download file from FTP. Aborting update.")
        return False
    
    # Validate the downloaded file
    if not validate_excel_file(Config.TEMP_FILE):
        logger.error("Downloaded file failed validation. Aborting update.")
        return False
    
    # Create a backup of the current file
    backup_current_file()
    
    # Load the new data into memory
    if not load_data_into_memory(Config.TEMP_FILE):
        logger.error("Failed to load data into memory. Aborting update.")
        return False
    
    # If all successful, replace the current file with the new one
    try:
        logger.info(f"Replacing current file with new file")
        shutil.move(Config.TEMP_FILE, Config.CURRENT_FILE)
        logger.info("Data update process completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error replacing current file: {str(e)}")
        return False

def get_initial_data():
    """Load initial data from the current file when the service starts"""
    global product_data_cache, last_update_time
    
    ensure_directories()
    
    if Config.CURRENT_FILE.exists():
        logger.info(f"Loading initial data from existing file: {Config.CURRENT_FILE}")
        if load_data_into_memory(Config.CURRENT_FILE):
            return product_data_cache
    
    logger.warning("No initial data file found")
    return {}

def start_scheduler():
    """Start the scheduler to run updates at the specified time"""
    schedule.every().day.at(Config.UPDATE_TIME).do(update_data)
    logger.info(f"Scheduled daily updates at {Config.UPDATE_TIME}")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def run_data_service():
    """Main function to run the data service"""
    logger.info("Starting data update service")
    
    # Load initial data
    get_initial_data()
    
    # Run an initial update if requested
    if os.environ.get('INITIAL_UPDATE', 'false').lower() == 'true':
        logger.info("Running initial update")
        update_data()
    
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("Data update service started successfully")
    return scheduler_thread

# If run as a script, start the service
if __name__ == "__main__":
    run_data_service()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(3600)  # Sleep for an hour
    except KeyboardInterrupt:
        logger.info("Data update service stopping")