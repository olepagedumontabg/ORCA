import os
import logging
from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import traceback
from logic import compatibility

# Configure app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure logging
logger = logging.getLogger(__name__)

# Initialize session data structure for search history
@app.before_request
def initialize_session():
    if 'search_history' not in session:
        session['search_history'] = []

@app.route('/')
def index():
    """Render the main page"""
    search_history = session.get('search_history', [])
    return render_template('index.html', search_history=search_history)

@app.route('/search', methods=['POST'])
def search():
    """Handle SKU search request"""
    try:
        sku = request.form.get('sku', '').strip().upper()
        
        if not sku:
            return jsonify({
                'success': False,
                'message': 'Please enter a SKU number'
            })
        
        # Log the search request
        logger.debug(f"Searching for SKU: {sku}")
        
        # Call the compatibility function to find matches
        results = compatibility.find_compatible_products(sku)
        
        # Update search history (most recent first, maximum 5 items)
        search_history = session.get('search_history', [])
        
        # Remove the SKU if it's already in history to avoid duplicates
        search_history = [s for s in search_history if s != sku]
        
        # Add the new SKU at the beginning
        search_history.insert(0, sku)
        
        # Keep only the 5 most recent searches
        search_history = search_history[:5]
        
        # Update session
        session['search_history'] = search_history
        
        if results and results['product']:
            # Log the product details for debugging
            logger.debug(f"Returning product: {results['product'].get('name', 'Unknown')} for SKU: {sku}")
            
            return jsonify({
                'success': True,
                'sku': sku,
                'product': results['product'],
                'compatibles': results['compatibles'],
                'search_history': search_history
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No product found for SKU {sku}',
                'search_history': search_history
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
