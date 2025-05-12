"""
Service Starter Script
Run this script to start the data updater and compatibility processor services.
"""
import os
import sys
import time
import signal
import subprocess
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('service_starter')

# Global process trackers
data_updater_process = None
compatibility_processor_process = None
running = True

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Received termination signal, shutting down services...")
    running = False
    stop_services()
    sys.exit(0)

def stop_services():
    """Stop all running services"""
    global data_updater_process, compatibility_processor_process
    
    if data_updater_process:
        logger.info("Stopping data updater service...")
        try:
            data_updater_process.terminate()
            data_updater_process.wait(timeout=5)
        except:
            data_updater_process.kill()
        data_updater_process = None
    
    if compatibility_processor_process:
        logger.info("Stopping compatibility processor service...")
        try:
            compatibility_processor_process.terminate()
            compatibility_processor_process.wait(timeout=5)
        except:
            compatibility_processor_process.kill()
        compatibility_processor_process = None

def start_data_updater():
    """Start the data updater service"""
    global data_updater_process
    try:
        logger.info("Starting data updater service...")
        data_updater_process = subprocess.Popen([sys.executable, 'data_updater.py'],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              universal_newlines=True)
        
        # Monitor the process output
        for line in data_updater_process.stdout:
            logger.info(f"[DATA UPDATER] {line.strip()}")
        
        # Check if process exited
        data_updater_process.wait()
        logger.warning("Data updater service exited unexpectedly!")
        data_updater_process = None
    except Exception as e:
        logger.error(f"Error in data updater service: {str(e)}")
        data_updater_process = None

def start_compatibility_processor():
    """Start the compatibility processor service"""
    global compatibility_processor_process
    try:
        logger.info("Starting compatibility processor service...")
        compatibility_processor_process = subprocess.Popen([sys.executable, 'compatibility_processor.py'],
                                                         stdout=subprocess.PIPE,
                                                         stderr=subprocess.STDOUT,
                                                         universal_newlines=True)
        
        # Monitor the process output
        for line in compatibility_processor_process.stdout:
            logger.info(f"[COMPATIBILITY] {line.strip()}")
        
        # Check if process exited
        compatibility_processor_process.wait()
        logger.warning("Compatibility processor service exited unexpectedly!")
        compatibility_processor_process = None
    except Exception as e:
        logger.error(f"Error in compatibility processor service: {str(e)}")
        compatibility_processor_process = None

def main():
    """Main function to start services"""
    logger.info("Starting background services...")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start data updater in a separate thread
    data_thread = threading.Thread(target=start_data_updater)
    data_thread.daemon = True
    data_thread.start()
    
    # Start compatibility processor in a separate thread
    compat_thread = threading.Thread(target=start_compatibility_processor)
    compat_thread.daemon = True
    compat_thread.start()
    
    logger.info("Services started successfully!")
    logger.info("Press Ctrl+C to stop services.")
    
    # Keep main thread alive until shutdown
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        stop_services()

if __name__ == "__main__":
    main()