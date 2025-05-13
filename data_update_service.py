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
    FTP_HOST = os.environ.get('FTP_HOST', '')
    FTP_USER = os.environ.get('FTP_USER', '')
    FTP_PASSWORD = os.environ.get('FTP_PASSWORD', '')
    FTP_PATH = os.environ.get('FTP_PATH', '/')
    FTP_FILENAME = os.environ.get('FTP_FILENAME', 'Product Data.xlsx')
    
    # Local paths
    DATA_DIR = Path('data')
    BACKUP_DIR = DATA_DIR / 'backup'
    CURRENT_FILE = DATA_DIR / 'Product Data.xlsx'
    TEMP_FILE = DATA_DIR / 'temp_product_data.xlsx'
    
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
    """Download the latest file from FTP server"""
    if not all([Config.FTP_HOST, Config.FTP_USER, Config.FTP_PASSWORD]):
        logger.error("FTP credentials not provided. Set FTP_HOST, FTP_USER, and FTP_PASSWORD environment variables.")
        return False
    
    try:
        logger.info(f"Connecting to FTP server {Config.FTP_HOST}")
        with ftplib.FTP(Config.FTP_HOST) as ftp:
            ftp.login(Config.FTP_USER, Config.FTP_PASSWORD)
            
            # Change to the specified directory
            if Config.FTP_PATH != '/':
                ftp.cwd(Config.FTP_PATH)
            
            # Check if file exists
            file_list = ftp.nlst()
            if Config.FTP_FILENAME not in file_list:
                logger.error(f"File {Config.FTP_FILENAME} not found on FTP server")
                return False
            
            # Download file
            logger.info(f"Downloading {Config.FTP_FILENAME} to {Config.TEMP_FILE}")
            with open(Config.TEMP_FILE, 'wb') as f:
                ftp.retrbinary(f'RETR {Config.FTP_FILENAME}', f.write)
            
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
        
        # Check for required worksheets
        required_sheets = ['Shower Bases', 'Shower Doors', 'Return Panels', 'Walls', 'Enclosures']
        missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]
        
        if missing_sheets:
            logger.error(f"Excel file missing required sheets: {', '.join(missing_sheets)}")
            return False
        
        # Check each worksheet for required columns
        required_columns = {
            'Shower Bases': ['Unique ID', 'Product Name', 'Nominal Dimensions', 'Length', 'Width'],
            'Shower Doors': ['Unique ID', 'Product Name', 'Min Width', 'Max Width'],
            'Return Panels': ['Unique ID', 'Product Name', 'Return Panel Size'],
            'Walls': ['Unique ID', 'Product Name', 'Nominal Dimensions'],
            'Enclosures': ['Unique ID', 'Product Name', 'Nominal Dimensions']
        }
        
        for sheet, columns in required_columns.items():
            df = pd.read_excel(file_path, sheet_name=sheet)
            missing_columns = [col for col in columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Sheet {sheet} missing required columns: {', '.join(missing_columns)}")
                return False
        
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