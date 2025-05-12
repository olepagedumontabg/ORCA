import os
import logging
import traceback
import json
from flask import render_template, request, jsonify, session
from main import app, db
from models import Product, Compatibility
from sqlalchemy import func

# Configure logging
logger = logging.getLogger(__name__)

# Routes module for the application
routes = app  # For importing in main.py

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
        
        # Find product in database
        product = Product.query.filter(Product.sku == sku).first()
        
        if not product:
            logger.warning(f"No product found for SKU: {sku}")
            # Update search history
            update_search_history(sku)
            return jsonify({
                'success': False,
                'message': f'No product found for SKU {sku}',
                'search_history': session.get('search_history', [])
            })
            
        # Debug output
        logger.debug(f"Found product: {product.sku} in category {product.category}")
        
        # Find compatible products
        compatibilities = Compatibility.query.filter(
            Compatibility.source_sku == sku
        ).all()
        
        # Organize results by category
        results = {}
        for compat in compatibilities:
            category = compat.target_category
            if category not in results:
                results[category] = []
            
            if compat.requires_return_panel:
                # Format with return panel info
                results[category].append(f"{compat.target_sku} (+ Return Panel: {compat.requires_return_panel})")
            else:
                results[category].append(compat.target_sku)
        
        # Format for the frontend
        formatted_results = []
        for category, skus in results.items():
            formatted_results.append({
                'category': category,
                'skus': skus
            })
        
        # Update search history
        update_search_history(sku)
        
        return jsonify({
            'success': True,
            'sku': sku,
            'data': formatted_results,
            'search_history': session.get('search_history', [])
        })
            
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

def update_search_history(sku):
    """Update the session search history"""
    search_history = session.get('search_history', [])
    
    # Remove the SKU if it's already in history to avoid duplicates
    search_history = [s for s in search_history if s != sku]
    
    # Add the new SKU at the beginning
    search_history.insert(0, sku)
    
    # Keep only the 5 most recent searches
    search_history = search_history[:5]
    
    # Update session
    session['search_history'] = search_history
    return search_history