import pandas as pd
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_excel_file(file_path):
    """
    Analyze the Excel file to identify worksheets and their data structure
    
    Args:
        file_path (str): Path to the Excel file
    """
    try:
        logger.info(f"Analyzing Excel file: {file_path}")
        
        # Get the list of sheet names
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        
        logger.info(f"Found {len(sheet_names)} worksheets: {sheet_names}")
        
        # Analyze each sheet
        for sheet_name in sheet_names:
            logger.info(f"\n\n--- Sheet: {sheet_name} ---")
            
            # Read the worksheet
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Basic info
            logger.info(f"Shape: {df.shape} (rows, columns)")
            
            # Column names and types
            logger.info("\nColumns:")
            for col in df.columns:
                dtype = df[col].dtype
                non_null_count = df[col].count()
                null_percentage = round((len(df) - non_null_count) / len(df) * 100, 2) if len(df) > 0 else 0
                
                sample_values = df[col].dropna().head(3).tolist()
                sample_str = str(sample_values)[:100] + "..." if len(str(sample_values)) > 100 else sample_values
                
                logger.info(f"  - {col} (Type: {dtype}, Null: {null_percentage}%) Sample: {sample_str}")
            
            # Check for a potential ID or SKU column
            potential_ids = [col for col in df.columns if 'id' in str(col).lower() or 'sku' in str(col).lower()]
            if potential_ids:
                logger.info(f"\nPotential ID/SKU columns: {potential_ids}")
            
            # Preview first few rows
            logger.info("\nData Preview (first 5 rows):")
            logger.info(df.head(5))
            
    except Exception as e:
        logger.error(f"Error analyzing Excel file: {str(e)}")

if __name__ == "__main__":
    # Get the path to the Excel file
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    excel_files = [f for f in os.listdir(data_path) if f.endswith('.xlsx')]
    
    if not excel_files:
        logger.error("No Excel files found in the data directory")
    else:
        # Analyze each Excel file
        for file_name in excel_files:
            file_path = os.path.join(data_path, file_name)
            analyze_excel_file(file_path)