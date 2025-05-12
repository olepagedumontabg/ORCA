"""
Test the dimension matching function in the compatibility processor.
This ensures that our dimension matching logic works correctly with 
all the different format variations we might encounter in the data.
"""
import pandas as pd
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_dimensions')

def match_nominal_dimensions(dim1, dim2):
    """
    Match nominal dimensions with format flexibility
    Handles variations like "48 x 32" vs "48x32" and unit conversions
    """
    if pd.isna(dim1) or pd.isna(dim2):
        return False
        
    # Direct string comparison (case-insensitive, whitespace trimmed)
    dim1_clean = str(dim1).strip().lower()
    dim2_clean = str(dim2).strip().lower()
    if dim1_clean == dim2_clean:
        return True
        
    # Remove all whitespace and compare
    dim1_nospace = re.sub(r'\s+', '', dim1_clean)
    dim2_nospace = re.sub(r'\s+', '', dim2_clean)
    if dim1_nospace == dim2_nospace:
        return True
        
    # Replace common variations of 'x' separator
    dim1_std = re.sub(r'[×xX*]', 'x', dim1_nospace)
    dim2_std = re.sub(r'[×xX*]', 'x', dim2_nospace)
    if dim1_std == dim2_std:
        return True
        
    # Split by 'x' and compare individual dimensions
    try:
        dim1_parts = dim1_std.split('x')
        dim2_parts = dim2_std.split('x')
        
        # Basic dimension comparison
        if len(dim1_parts) == 2 and len(dim2_parts) == 2:
            # Extract numeric values if possible
            try:
                dim1_width = float(re.match(r'(\d+(?:\.\d+)?)', dim1_parts[0]).group(1))
                dim1_depth = float(re.match(r'(\d+(?:\.\d+)?)', dim1_parts[1]).group(1))
                dim2_width = float(re.match(r'(\d+(?:\.\d+)?)', dim2_parts[0]).group(1))
                dim2_depth = float(re.match(r'(\d+(?:\.\d+)?)', dim2_parts[1]).group(1))
                
                # Check if dimensions match with a small tolerance
                width_match = abs(dim1_width - dim2_width) <= 0.5
                depth_match = abs(dim1_depth - dim2_depth) <= 0.5
                
                if width_match and depth_match:
                    return True
            except:
                # If numeric extraction fails, fallback to exact string match
                return dim1_parts[0] == dim2_parts[0] and dim1_parts[1] == dim2_parts[1]
    except:
        pass
        
    # Handle special cases like fractions or unit conversions
    # This would be expanded based on observed data patterns
        
    return False

def run_tests():
    """Run a comprehensive set of tests for the dimension matching function"""
    test_cases = [
        # Exact matches
        ("48 x 32", "48 x 32", True),
        ("48x32", "48x32", True),
        
        # Whitespace variations
        ("48 x 32", "48x32", True),
        ("48x32", "48 x 32", True),
        ("48  x  32", "48x32", True),
        (" 48 x 32 ", "48x32", True),
        
        # Separator variations
        ("48 x 32", "48X32", True),
        ("48x32", "48×32", True),
        ("48*32", "48x32", True),
        
        # Case variations
        ("48 X 32", "48 x 32", True),
        ("48X32", "48x32", True),
        
        # Small numeric variations (within tolerance)
        ("48.2 x 32", "48 x 32", True),
        ("48 x 32.3", "48 x 32", True),
        ("47.8 x 31.6", "48 x 32", True),
        
        # Larger variations (outside tolerance)
        ("49 x 32", "48 x 32", False),
        ("48 x 33", "48 x 32", False),
        
        # Different dimensions
        ("60 x 32", "48 x 32", False),
        ("48 x 36", "48 x 32", False),
        
        # Invalid formats
        ("48", "48 x 32", False),
        ("48 x 32", "unknown", False),
        ("48 x 32", None, False),
        (None, "48 x 32", False),
        (None, None, False),
    ]
    
    all_passed = True
    
    for i, (dim1, dim2, expected) in enumerate(test_cases):
        result = match_nominal_dimensions(dim1, dim2)
        passed = result == expected
        
        if not passed:
            all_passed = False
            logger.error(f"Test {i+1} failed: '{dim1}' vs '{dim2}' => {result}, expected {expected}")
        else:
            logger.info(f"Test {i+1} passed: '{dim1}' vs '{dim2}' => {result}")
    
    if all_passed:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed, see above for details")
    
    return all_passed

if __name__ == "__main__":
    logger.info("Starting dimension matching tests...")
    run_tests()