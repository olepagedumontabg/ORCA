import os
import logging
import threading
from flask import Flask, render_template, request, jsonify, send_file, abort
import pandas as pd
import io
import traceback
from logic import compatibility
import data_loader

# Try to import the data update service
try:
    import data_update_service
    data_service_available = True
except ImportError:
    data_service_available = False

# Configure app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Initialize data update service
data_update_thread = None
if data_service_available:
    try:
        # Import locally within the conditional
        import data_update_service as data_service
        logger.info("Initializing data update service")
        data_update_thread = threading.Thread(
            target=data_service.run_data_service, daemon=True)
        data_update_thread.start()
        logger.info("Data update service thread started")
    except Exception as e:
        logger.error(f"Failed to start data update service: {str(e)}")
        data_service_available = False


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


@app.route('/documentation')
def documentation():
    """Render the documentation page"""
    return render_template('documentation.html')


@app.route("/download/<sku>")
def download_compatibilities(sku):
    """
    Generate an .xlsx file (single worksheet) listing all compatible products for `sku`.
    Columns: SKU | Name | Product Page URL | Brand | Series
    """
    result = compatibility.find_compatible_products(sku)
    if result.get("product") is None:
        return abort(404, "SKU not found")

    # Collect all compatible products across categories into one list
    all_products = []
    for cat in result.get("compatibles", []):
        for p in cat.get("products", []):
            all_products.append(p)

    if not all_products:
        return abort(404, "No compatible products found")

    df = pd.DataFrame(all_products)

    # Map possible column names
    column_map = {
        "sku": "SKU",
        "name": "Name",
        "product_page_url": "Product Page URL",
        "product_page": "Product Page URL",
        "url": "Product Page URL",
        "brand": "Brand",
        "series": "Series"
    }

    # Keep only columns that exist
    available = {k: v for k, v in column_map.items() if k in df.columns}
    if not available:
        logger.warning(
            "None of the expected columns found in dataframe columns=%s",
            list(df.columns))
        return abort(500, "Unexpected data format")

    df = df[list(available.keys())].rename(columns=available)

    # Remove duplicates
    df = df.drop_duplicates()

    # Build Excel workbook
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as xl:
        df.to_excel(xl, sheet_name="Compatibilities", index=False)

    output.seek(0)
    filename = f"compatibilities_{sku}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route('/simple')
def simple():
    """Render the simplified page for testing"""
    return render_template('simple.html')


@app.route('/suggest', methods=['GET'])
def suggest_skus():
    """Provide SKU suggestions based on partial input (SKU or product name)"""
    try:
        query = request.args.get('q', '').strip().upper()

        if not query or len(query) < 3:
            # Return empty results if query is too short
            return jsonify({'suggestions': [], 'displaySuggestions': []})

        # Get all SKUs from the data
        data = compatibility.load_data()

        # Dictionary to store SKU and product name pairs
        sku_product_map = {}

        # Collect SKUs and product names from all sheets
        for sheet_name, df in data.items():
            # Look for 'Unique ID' column which contains the SKUs
            if 'Unique ID' in df.columns:
                # Check if 'Product Name' column exists
                product_name_col = 'Product Name' if 'Product Name' in df.columns else None

                # Iterate through rows to collect SKU and product name pairs
                for _, row in df.iterrows():
                    sku = str(row['Unique ID'])
                    product_name = str(
                        row[product_name_col]) if product_name_col else ''
                    sku_product_map[sku] = product_name

        # Find matches by SKU
        matching_skus_by_id = [
            sku for sku in sku_product_map.keys() if query in sku
        ]

        # Find matches by product name
        matching_skus_by_name = []
        for sku, product_name in sku_product_map.items():
            if product_name and query in product_name.upper():
                matching_skus_by_name.append(sku)

        # Combine unique matches, prioritizing SKU matches
        matching_skus = list(
            dict.fromkeys(matching_skus_by_id + matching_skus_by_name))

        # Sort and limit results
        matching_skus.sort()
        matching_skus = matching_skus[:10]  # Limit to top 10 matches

        # Create display suggestions with SKU and product name
        display_suggestions = []
        for sku in matching_skus:
            product_name = sku_product_map.get(sku, '')
            if product_name:
                display_suggestions.append(f"{sku} - {product_name}")
            else:
                display_suggestions.append(sku)

        # Log the number of suggestions for debugging
        logger.debug(
            f"Found {len(matching_skus)} suggestions for query '{query}' (SKU: {len(matching_skus_by_id)}, Name: {len(matching_skus_by_name)})"
        )

        return jsonify({
            'suggestions': matching_skus,  # Original SKUs for selection
            'displaySuggestions':
            display_suggestions  # Formatted display strings
        })

    except Exception as e:
        logger.error(f"Error in suggest_skus: {str(e)}")
        return jsonify({
            'suggestions': [],
            'displaySuggestions': [],
            'error': str(e)
        })


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

        # ---------------------------------------------------------------
        # Build the incompatibility_reasons object for the front‑end
        # First, get any incompatibility reasons from the results directly
        incompatibility_reasons = results.get("incompatibility_reasons", {})
        
        # Then, add any incompatibility reasons from compatibles array (for backward compatibility)
        for cat in results.get("compatibles", []):
            if cat.get("reason") and not cat.get("products"):
                incompatibility_reasons[cat["category"]] = cat.get("reason", "")
        # ---------------------------------------------------------------


        if results and results['product']:
            # Log the product details for debugging
            product_name = results['product'].get('name', 'Unknown')
            product_category = results['product'].get('category',
                                                      'Unknown Category')
            logger.debug(
                f"Returning product: {product_name} from category: {product_category} for SKU: {sku}"
            )

            # Create a clean response object without any NaN values
            clean_response = {
                'success': True,
                'sku': sku,
                'product': results['product'],
                'compatibles': results['compatibles'],
                'incompatibility_reasons': incompatibility_reasons      # ← add this
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
                elif isinstance(obj,
                                (float, int)) and (pd.isna(obj) if hasattr(
                                    pd, 'isna') else False):
                    return None
                # Safely handle pandas objects
                elif hasattr(pd, 'isna') and hasattr(pd, 'api') and hasattr(
                        pd.api, 'types'):
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
                clean_json_str = json.dumps(clean_response,
                                            default=custom_json_default)
                return jsonify(json.loads(clean_json_str))
            except Exception as e:
                logger.error(f"JSON serialization error: {str(e)}")
                # Fallback to a simpler response with string conversion
                safe_response = {
                    'success':
                    True,
                    'sku':
                    str(sku),
                    'product': {
                        k: str(v) if not isinstance(v, (dict, list)) else v
                        for k, v in results['product'].items()
                    },
                    'compatibles': [{
                        'category':
                        c.get('category', ''),
                        'products': [{
                            k:
                            str(v) if not isinstance(v, (dict, list)) else v
                            for k, v in p.items()
                        } for p in c.get('products', [])]
                    } for c in results['compatibles']],
                    'incompatibility_reasons': incompatibility_reasons  # ← add this'
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


# ============================================================================
# REST API ENDPOINTS FOR EXTERNAL ACCESS
# ============================================================================

@app.route('/api/compatible/<sku>', methods=['GET'])
def api_get_compatible(sku):
    """
    REST API endpoint to get compatible products for a given SKU.
    
    Returns JSON with product details and all compatible products.
    
    Query Parameters:
        - category: Filter by category (optional)
        - limit: Limit results per category (optional, default: 100)
    
    Example: GET /api/compatible/FB03060M
    Example: GET /api/compatible/FB03060M?category=Doors&limit=20
    """
    try:
        sku = sku.strip().upper()
        category_filter = request.args.get('category', '').strip()
        limit = request.args.get('limit', type=int, default=100)
        
        logger.info(f"API request for compatible products: SKU={sku}")
        
        db_compatibles = None
        if data_loader.check_database_ready():
            logger.info(f"Attempting to load compatibilities from database for {sku}")
            db_compatibles = data_loader.load_compatible_products_from_database(sku)
        
        if db_compatibles is not None:
            logger.info(f"Using database-sourced compatibilities for {sku}")
            product_data = data_loader.load_product_from_database(sku)
            
            if not product_data:
                return jsonify({
                    'success': False,
                    'error': 'Product not found',
                    'sku': sku
                }), 404
            
            compatibles = []
            for category, products in db_compatibles.items():
                if category_filter and category.lower() != category_filter.lower():
                    continue
                
                if len(products) > limit:
                    compatibles.append({
                        'category': category,
                        'products': products[:limit],
                        'truncated': True,
                        'total_count': len(products)
                    })
                else:
                    compatibles.append({
                        'category': category,
                        'products': products
                    })
            
            response = {
                'success': True,
                'sku': sku,
                'product': {
                    'sku': product_data.get('Unique ID'),
                    'name': product_data.get('Product Name'),
                    'brand': product_data.get('Brand'),
                    'category': product_data.get('Category'),
                    'series': product_data.get('Series'),
                    'family': product_data.get('Family'),
                    'image_url': product_data.get('Image URL'),
                    'product_page_url': product_data.get('Product Page URL'),
                },
                'compatibles': compatibles,
                'incompatibility_reasons': {},
                'total_categories': len(compatibles),
                'data_source': 'database'
            }
            
            return jsonify(response)
        
        logger.info(f"Falling back to Excel-based compatibility for {sku}")
        results = compatibility.find_compatible_products(sku)
        
        if not results or not results.get('product'):
            return jsonify({
                'success': False,
                'error': 'Product not found',
                'sku': sku
            }), 404
        
        incompatibility_reasons = results.get("incompatibility_reasons", {})
        for cat in results.get("compatibles", []):
            if cat.get("reason") and not cat.get("products"):
                incompatibility_reasons[cat["category"]] = cat.get("reason", "")
        
        compatibles = results.get('compatibles', [])
        
        if category_filter:
            compatibles = [c for c in compatibles if c.get('category', '').lower() == category_filter.lower()]
        
        for cat in compatibles:
            products = cat.get('products', [])
            if len(products) > limit:
                cat['products'] = products[:limit]
                cat['truncated'] = True
                cat['total_count'] = len(products)
        
        response = {
            'success': True,
            'sku': sku,
            'product': results['product'],
            'compatibles': compatibles,
            'incompatibility_reasons': incompatibility_reasons,
            'total_categories': len(compatibles),
            'data_source': 'excel'
        }
        
        import pandas as pd
        import json
        
        def deep_clean(obj):
            if isinstance(obj, (list, tuple)):
                return [deep_clean(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: deep_clean(v) for k, v in obj.items()}
            elif obj is None:
                return None
            elif isinstance(obj, (float, int)) and (pd.isna(obj) if hasattr(pd, 'isna') else False):
                return None
            elif hasattr(pd, 'isna') and hasattr(pd, 'api') and hasattr(pd.api, 'types'):
                if pd.api.types.is_scalar(obj) and pd.isna(obj):
                    return None
                else:
                    return obj
            else:
                return obj
        
        response = deep_clean(response)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"API error for compatible/{sku}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'sku': sku
        }), 500


@app.route('/api/product/<sku>', methods=['GET'])
def api_get_product(sku):
    """
    REST API endpoint to get details about a specific product.
    
    Returns JSON with product details only (no compatibility data).
    
    Example: GET /api/product/FB03060M
    """
    try:
        sku = sku.strip().upper()
        
        logger.info(f"API request for product details: SKU={sku}")
        
        if data_loader.check_database_ready():
            logger.info(f"Attempting to load product from database: {sku}")
            product_data = data_loader.load_product_from_database(sku)
            
            if product_data:
                import pandas as pd
                product_clean = {}
                for k, v in product_data.items():
                    if pd.isna(v):
                        product_clean[k] = None
                    else:
                        product_clean[k] = v
                
                return jsonify({
                    'success': True,
                    'sku': sku,
                    'category': product_clean.get('Category'),
                    'product': product_clean,
                    'data_source': 'database'
                })
        
        logger.info(f"Falling back to Excel for product: {sku}")
        data = compatibility.load_data()
        
        for sheet_name, df in data.items():
            if 'Unique ID' in df.columns:
                matching_rows = df[df['Unique ID'].astype(str).str.upper() == sku]
                if not matching_rows.empty:
                    product_data = matching_rows.iloc[0].to_dict()
                    
                    import pandas as pd
                    product_clean = {}
                    for k, v in product_data.items():
                        if pd.isna(v):
                            product_clean[k] = None
                        else:
                            product_clean[k] = v
                    
                    return jsonify({
                        'success': True,
                        'sku': sku,
                        'category': sheet_name,
                        'product': product_clean,
                        'data_source': 'excel'
                    })
        
        return jsonify({
            'success': False,
            'error': 'Product not found',
            'sku': sku
        }), 404
        
    except Exception as e:
        logger.error(f"API error for product/{sku}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'sku': sku
        }), 500


@app.route('/api/products', methods=['GET'])
def api_list_products():
    """
    REST API endpoint to list all products.
    
    Query Parameters:
        - category: Filter by category (optional)
        - brand: Filter by brand (optional)
        - limit: Number of results to return (default: 100, max: 1000)
        - offset: Number of results to skip (default: 0)
    
    Example: GET /api/products
    Example: GET /api/products?category=Shower Bases&brand=Swan&limit=50
    """
    try:
        category_filter = request.args.get('category', '').strip()
        brand_filter = request.args.get('brand', '').strip().lower()
        limit = min(request.args.get('limit', type=int, default=100), 1000)
        offset = request.args.get('offset', type=int, default=0)
        
        logger.info(f"API request for products list: category={category_filter}, brand={brand_filter}, limit={limit}, offset={offset}")
        
        if data_loader.check_database_ready():
            logger.info("Loading products from database")
            db_products, total_count = data_loader.get_all_products_from_database(
                category=category_filter if category_filter else None,
                limit=limit,
                offset=offset
            )
            
            if brand_filter:
                db_products = [p for p in db_products if brand_filter in str(p.get('Brand', '')).lower()]
                total_count = len(db_products)
            
            import pandas as pd
            clean_products = []
            for product in db_products:
                product_clean = {}
                for k, v in product.items():
                    if pd.isna(v):
                        product_clean[k] = None
                    else:
                        product_clean[k] = v
                clean_products.append(product_clean)
            
            return jsonify({
                'success': True,
                'products': clean_products,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'returned_count': len(clean_products),
                'data_source': 'database'
            })
        
        logger.info("Falling back to Excel for products list")
        data = compatibility.load_data()
        all_products = []
        
        for sheet_name, df in data.items():
            if category_filter and sheet_name.lower() != category_filter.lower():
                continue
            
            if 'Unique ID' in df.columns:
                for _, row in df.iterrows():
                    product_dict = row.to_dict()
                    
                    if brand_filter:
                        product_brand = str(product_dict.get('Brand', '')).lower()
                        if brand_filter not in product_brand:
                            continue
                    
                    import pandas as pd
                    product_clean = {'category': sheet_name}
                    for k, v in product_dict.items():
                        if pd.isna(v):
                            product_clean[k] = None
                        else:
                            product_clean[k] = v
                    
                    all_products.append(product_clean)
        
        total_count = len(all_products)
        paginated_products = all_products[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'products': paginated_products,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'returned_count': len(paginated_products),
            'data_source': 'excel'
        })
        
    except Exception as e:
        logger.error(f"API error for products list: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories', methods=['GET'])
def api_list_categories():
    """
    REST API endpoint to list all available product categories.
    
    Returns JSON with category names and product counts.
    
    Example: GET /api/categories
    """
    try:
        logger.info("API request for categories list")
        
        data = compatibility.load_data()
        categories = []
        
        for sheet_name, df in data.items():
            if 'Unique ID' in df.columns:
                categories.append({
                    'name': sheet_name,
                    'product_count': len(df)
                })
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_categories': len(categories)
        })
        
    except Exception as e:
        logger.error(f"API error for categories list: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """
    Health check endpoint for monitoring.
    
    Returns system status and data freshness information.
    
    Example: GET /api/health
    """
    try:
        data_source_info = data_loader.get_data_source_info()
        
        data = compatibility.load_data()
        total_products = sum(len(df) for df in data.values())
        
        health_status = {
            'success': True,
            'status': 'healthy',
            'total_products': total_products,
            'categories': len(data),
            'data_service_available': data_service_available,
            'data_source': data_source_info
        }
        
        if data_service_available:
            try:
                import data_update_service as data_service
                cached_data, update_time = data_service.get_product_data()
                if update_time:
                    health_status['last_data_update'] = update_time.isoformat()
            except Exception:
                pass
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"API error for health check: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ============================================================================
# END OF REST API ENDPOINTS
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
