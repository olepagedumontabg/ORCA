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
            
            return jsonify({
                'success': True,
                'sku': sku,
                'product': results['product'],
                'compatibles': results['compatibles']
            })
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
