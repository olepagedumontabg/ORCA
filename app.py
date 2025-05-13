import os
import logging
from flask import Flask, render_template, request, jsonify
import pandas as pd
import traceback
from logic import compatibility

# Configure app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure logging
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/simple')
def simple():
    """Render the simplified page for testing"""
    return render_template('simple.html')

@app.route('/search', methods=['POST'])
def search():
    """Handle SKU search request"""
    try:
        # Check if the request is JSON or form data
        if request.is_json:
            data = request.json
            sku = data.get('sku', '') if data else ''
        else:
            sku = request.form.get('sku', '')
            
        # Normalize the SKU
        sku = sku.strip().upper() if sku else ''
        
        if not sku:
            return jsonify({
                'success': False,
                'message': 'Please enter a SKU number'
            })
        
        # Log the search request
        logger.debug(f"Searching for SKU: {sku}")
        
        # Call the compatibility function to find matches
        results = compatibility.find_compatible_products(sku)
        
        if results and results['product']:
            # Log the product details for debugging
            product_name = results['product'].get('name', 'Unknown')
            product_category = results['product'].get('category', 'Unknown Category')
            logger.debug(f"Returning product: {product_name} from category: {product_category} for SKU: {sku}")
            
            # Create a clean response object without any NaN values
            clean_response = {
                'success': True,
                'sku': sku,
                'product': results['product'],
                'compatibles': results['compatibles']
            }
            
            # Import pandas and json at the top of the function for better clarity
            import pandas as pd
            import json
            
            # Deep clean function to replace NaN, None and other problematic values
            def deep_clean(obj):
                # Handle arrays and pandas objects safely
                if isinstance(obj, (list, tuple)):
                    return [deep_clean(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: deep_clean(v) for k, v in obj.items()}
                # Check for None first to avoid unnecessary pd.isna calls
                elif obj is None:
                    return None
                # Use safer check for NaN values
                elif isinstance(obj, (float, int)) and (pd.isna(obj) if hasattr(pd, 'isna') else False):
                    return None
                # Safely handle pandas objects
                elif hasattr(pd, 'isna') and hasattr(pd, 'api') and hasattr(pd.api, 'types'):
                    # Handle pandas Series or DataFrame
                    if pd.api.types.is_scalar(obj) and pd.isna(obj):
                        return None
                    else:
                        return obj
                else:
                    return obj
            
            # Apply deep cleaning to the entire response
            clean_response = deep_clean(clean_response)
            
            # Serialize to JSON with error handling
            try:
                # Create a custom JSON encoder that safely handles all types
                def custom_json_default(obj):
                    if pd.isna(obj) if hasattr(pd, 'isna') else False:
                        return None
                    elif hasattr(obj, 'isoformat'):  # Handle date/time objects
                        return obj.isoformat()
                    elif isinstance(obj, (complex, bytes, bytearray)):
                        return str(obj)
                    else:
                        return str(obj)  # Last resort, convert to string
                
                # Convert to JSON string and back to ensure all values are JSON-compatible
                clean_json_str = json.dumps(clean_response, default=custom_json_default)
                return jsonify(json.loads(clean_json_str))
            except Exception as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Fallback to a simpler response with string conversion
                safe_response = {
                    'success': True,
                    'sku': str(sku),
                    'product': {k: str(v) if not isinstance(v, (dict, list)) else v for k, v in results['product'].items()},
                    'compatibles': [{
                        'category': c.get('category', ''),
                        'products': [{k: str(v) if not isinstance(v, (dict, list)) else v for k, v in p.items()} 
                                     for p in c.get('products', [])]
                    } for c in results['compatibles']]
                }
                return jsonify(safe_response)
        else:
            return jsonify({
                'success': False,
                'message': f'No product found for SKU {sku}'
            })
            
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
