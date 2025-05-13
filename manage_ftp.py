#!/usr/bin/env python3
"""
FTP Credentials Management Tool

This script helps set up and manage FTP credentials for data updates.
It also allows manual data updates from the FTP server.
"""

import os
import sys
import argparse
import logging
import dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ftp_manager")

# Try to import the data update service
try:
    import data_update_service
    data_service_available = True
except ImportError:
    data_service_available = False
    logger.error("Data update service not available. Make sure data_update_service.py exists.")

def save_credentials(args):
    """Save FTP credentials to environment variables or .env file"""
    try:
        # Create .env file if it doesn't exist
        env_file = Path('.env')
        if not env_file.exists():
            env_file.touch()
            logger.info("Created .env file")
        
        # Load existing variables
        dotenv.load_dotenv()
        
        # Update .env file with new credentials
        updated = False
        if args.host:
            os.environ["FTP_HOST"] = args.host
            dotenv.set_key('.env', "FTP_HOST", args.host)
            updated = True
        
        if args.user:
            os.environ["FTP_USER"] = args.user
            dotenv.set_key('.env', "FTP_USER", args.user)
            updated = True
        
        if args.password:
            os.environ["FTP_PASSWORD"] = args.password
            dotenv.set_key('.env', "FTP_PASSWORD", args.password)
            updated = True
        
        if args.path:
            os.environ["FTP_PATH"] = args.path
            dotenv.set_key('.env', "FTP_PATH", args.path)
            updated = True
        
        if args.filename:
            os.environ["FTP_FILENAME"] = args.filename
            dotenv.set_key('.env', "FTP_FILENAME", args.filename)
            updated = True
            
        if args.update_time:
            os.environ["UPDATE_TIME"] = args.update_time
            dotenv.set_key('.env', "UPDATE_TIME", args.update_time)
            updated = True
        
        if updated:
            logger.info("Successfully updated FTP credentials in .env file")
        else:
            logger.info("No changes made to FTP credentials")
            
    except Exception as e:
        logger.error(f"Error saving credentials: {str(e)}")
        return False
    
    return True

def show_credentials():
    """Show current FTP credentials (without showing the password)"""
    try:
        # Load environment variables
        dotenv.load_dotenv()
        
        print("\nCurrent FTP Configuration:")
        print(f"FTP Host: {os.environ.get('FTP_HOST', 'Not set')}")
        print(f"FTP User: {os.environ.get('FTP_USER', 'Not set')}")
        print(f"FTP Password: {'*' * 8 if os.environ.get('FTP_PASSWORD') else 'Not set'}")
        print(f"FTP Path: {os.environ.get('FTP_PATH', '/')}")
        print(f"FTP Filename: {os.environ.get('FTP_FILENAME', 'Product Data.xlsx')}")
        print(f"Update Time: {os.environ.get('UPDATE_TIME', '02:00')}")
        print("")
        
    except Exception as e:
        logger.error(f"Error showing credentials: {str(e)}")
        return False
    
    return True

def run_update():
    """Run a manual update from the FTP server"""
    # Import data_update_service locally to handle the case where it's not available
    try:
        import data_update_service
        data_service_available = True
    except ImportError:
        logger.error("Data update service is not available")
        print("Error: Data update service is not available")
        return False
    
    try:
        logger.info("Starting manual update from FTP server")
        result = data_update_service.update_data()
        
        if result:
            logger.info("Manual update completed successfully")
            print("Manual update completed successfully")
        else:
            logger.error("Manual update failed")
            print("Error: Manual update failed")
            return False
            
    except Exception as e:
        logger.error(f"Error running manual update: {str(e)}")
        print(f"Error running manual update: {str(e)}")
        return False
    
    return True

def test_connection():
    """Test connection to the FTP server"""
    # Import services locally
    try:
        import data_update_service
    except ImportError:
        logger.error("Data update service is not available")
        print("Error: Data update service is not available")
        return False
    
    try:
        # Load environment variables
        dotenv.load_dotenv()
        
        # Check if FTP credentials are set
        if not all([os.environ.get('FTP_HOST'), os.environ.get('FTP_USER'), os.environ.get('FTP_PASSWORD')]):
            logger.error("FTP credentials are not fully set. Use 'save' command to set them.")
            print("Error: FTP credentials are not fully set. Use 'save' command to set them.")
            return False
        
        logger.info("Testing connection to FTP server")
        print("Testing connection to FTP server...")
        
        # Initialize the FTP client
        import ftplib
        
        # Get FTP credentials from environment variables
        ftp_host = os.environ.get('FTP_HOST')
        ftp_user = os.environ.get('FTP_USER')
        ftp_password = os.environ.get('FTP_PASSWORD')
        ftp_path = os.environ.get('FTP_PATH', '/')
        
        if not ftp_host or not ftp_user or not ftp_password:
            logger.error("FTP credentials are missing")
            print("Error: FTP credentials are missing")
            return False
        
        # Try to connect to the FTP server
        with ftplib.FTP(ftp_host) as ftp:
            ftp.login(ftp_user, ftp_password)
            
            # Change to the specified directory
            if ftp_path != '/':
                ftp.cwd(ftp_path)
            
            # List directory contents
            files = ftp.nlst()
            
            # Check for files with the prefix
            prefix = 'Product Data'
            matching_files = [f for f in files if f.startswith(prefix)]
            
            if matching_files:
                # Sort files to get the most recent one
                matching_files.sort(reverse=True)
                newest_file = matching_files[0]
                logger.info(f"Found newest file: {newest_file} on FTP server")
                print(f"Found newest file: {newest_file} on FTP server")
            else:
                logger.warning(f"No files with prefix '{prefix}' found on FTP server")
                print(f"WARNING: No files with prefix '{prefix}' found on FTP server")
            
            logger.info("Connection to FTP server successful")
            print("Connection to FTP server successful")
            
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        print(f"Connection failed: {str(e)}")
        return False
    
    return True

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="FTP Credentials Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Save credentials command
    save_parser = subparsers.add_parser("save", help="Save FTP credentials")
    save_parser.add_argument("--host", help="FTP server hostname")
    save_parser.add_argument("--user", help="FTP username")
    save_parser.add_argument("--password", help="FTP password")
    save_parser.add_argument("--path", help="FTP directory path")
    save_parser.add_argument("--filename", help="Excel filename on FTP server")
    save_parser.add_argument("--update-time", help="Daily update time (24-hour format, e.g., '02:00')")
    
    # Show credentials command
    subparsers.add_parser("show", help="Show current FTP credentials")
    
    # Test connection command
    subparsers.add_parser("test", help="Test connection to FTP server")
    
    # Update command
    subparsers.add_parser("update", help="Run a manual update from the FTP server")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the specified command
    if args.command == "save":
        save_credentials(args)
    elif args.command == "show":
        show_credentials()
    elif args.command == "test":
        test_connection()
    elif args.command == "update":
        run_update()
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main()