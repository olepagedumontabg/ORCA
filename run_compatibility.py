"""
Run the compatibility processor to generate compatibility data for the database.
This script loads data from Excel files, processes compatibility, and stores in the database.
"""
from compatibility_processor import CompatibilityProcessor

if __name__ == "__main__":
    print("Starting compatibility processing...")
    processor = CompatibilityProcessor()
    processor.run_compatibility_process()
    print("Processing complete. Compatibility data stored in database.")