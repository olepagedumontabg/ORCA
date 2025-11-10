import os
import logging
import threading
from functools import lru_cache
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

# In-memory cache for API responses (LRU cache with 1000 entries)
_api_cache = {}
_cache_lock = threading.Lock()
_cache_max_size = 1000

def get_cached_compatibles(cache_key):
    """Get cached compatible products response"""
    with _cache_lock:
        return _api_cache.get(cache_key)

def cache_compatibles(cache_key, data):
    """Cache compatible products response with LRU eviction"""
    with _cache_lock:
        if len(_api_cache) >= _cache_max_size:
            # Remove oldest entry (simple FIFO for now)
            oldest = next(iter(_api_cache))
            del _api_cache[oldest]
        _api_cache[cache_key] = data

def clear_api_cache():
    """Clear all cached API responses (call after data updates)"""
    global _api_cache
    with _cache_lock:
        _api_cache.clear()
        logger.info("API cache cleared")

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


@app.route('/sync-history')
def sync_history():
    """Render the sync history page showing all webhook operations"""
    from models import get_session, SyncStatus
    from sqlalchemy import desc
    
    session = get_session()
    try:
        syncs = session.query(SyncStatus).order_by(desc(SyncStatus.started_at)).limit(100).all()
        logger.info(f"Sync history page: Found {len(syncs)} syncs in database")
        
        sync_list = []
        for sync in syncs:
            sync_data = {
                'id': sync.id,
                'sync_type': sync.sync_type,
                'status': sync.status,
                'started_at': sync.started_at,
                'completed_at': sync.completed_at,
                'products_added': sync.products_added or 0,
                'products_updated': sync.products_updated or 0,
                'products_deleted': sync.products_deleted or 0,
                'compatibilities_updated': sync.compatibilities_updated or 0,
                'error_message': sync.error_message,
                'metadata': sync.sync_metadata or {}
            }
            sync_list.append(sync_data)
            logger.info(f"  Sync #{sync.id}: {sync.status}")
        
        return render_template('sync_history.html', syncs=sync_list)
    finally:
        session.close()


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


@app.route('/suggest', methods=['GET'])
def suggest_skus():
    """Provide SKU suggestions based on partial input (SKU or product name)"""
    try:
        query = request.args.get('q', '').strip().upper()

        if not query or len(query) < 3:
            # Return empty results if query is too short
            return jsonify({'suggestions': [], 'displaySuggestions': []})

        # Try to use database first, fall back to Excel if needed
        from data_loader import check_database_ready
        from models import get_session, Product
        
        if check_database_ready():
            # Use database with optimized query
            session = get_session()
            try:
                # Optimize: Search SKU first (exact prefix match is fastest), then name
                # Use UPPER() for case-insensitive comparison which is faster with index
                from sqlalchemy import func, or_
                
                # Prioritize SKU matches (starts with query)
                sku_matches = session.query(Product.sku, Product.product_name).filter(
                    func.upper(Product.sku).like(f'{query}%')
                ).limit(10).all()
                
                # If we have enough SKU matches, return those
                if len(sku_matches) >= 5:
                    matching_skus = []
                    display_suggestions = []
                    for sku, product_name in sku_matches:
                        matching_skus.append(sku)
                        if product_name:
                            display_suggestions.append(f"{sku} - {product_name}")
                        else:
                            display_suggestions.append(sku)
                    
                    return jsonify({
                        'suggestions': matching_skus,
                        'displaySuggestions': display_suggestions
                    })
                
                # Otherwise, also search in product names
                all_matches = session.query(Product.sku, Product.product_name).filter(
                    or_(
                        func.upper(Product.sku).like(f'%{query}%'),
                        func.upper(Product.product_name).like(f'%{query}%')
                    )
                ).limit(10).all()
                
                matching_skus = []
                display_suggestions = []
                for sku, product_name in all_matches:
                    matching_skus.append(sku)
                    if product_name:
                        display_suggestions.append(f"{sku} - {product_name}")
                    else:
                        display_suggestions.append(sku)
                
                return jsonify({
                    'suggestions': matching_skus,
                    'displaySuggestions': display_suggestions
                })
            finally:
                session.close()
        else:
            # Fallback to Excel data
            data = compatibility.load_data()
            sku_product_map = {}

            for sheet_name, df in data.items():
                if 'Unique ID' in df.columns:
                    product_name_col = 'Product Name' if 'Product Name' in df.columns else None
                    for _, row in df.iterrows():
                        sku = str(row['Unique ID'])
                        product_name = str(row[product_name_col]) if product_name_col else ''
                        sku_product_map[sku] = product_name

            matching_skus_by_id = [sku for sku in sku_product_map.keys() if query in sku]
            matching_skus_by_name = [sku for sku, name in sku_product_map.items() if name and query in name.upper()]
            
            matching_skus = list(dict.fromkeys(matching_skus_by_id + matching_skus_by_name))
            matching_skus.sort()
            matching_skus = matching_skus[:10]

            display_suggestions = []
            for sku in matching_skus:
                product_name = sku_product_map.get(sku, '')
                if product_name:
                    display_suggestions.append(f"{sku} - {product_name}")
                else:
                    display_suggestions.append(sku)

            logger.debug(f"Found {len(matching_skus)} suggestions from Excel for query '{query}'")

            return jsonify({
                'suggestions': matching_skus,
                'displaySuggestions': display_suggestions
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
    
    Supports multi-SKU lookup with priority matching:
    1. Child SKU (path parameter)
    2. Parent SKU (query parameter)
    3. Unique ID (query parameter)
    
    Query Parameters:
        - parent_sku: Parent SKU for compatibility lookup (optional)
        - unique_id: Unique ID for compatibility lookup (optional)
        - category: Filter by category (optional)
        - limit: Limit results per category (optional, default: 100)
    
    Example: GET /api/compatible/410000-501-001-000?parent_sku=410000&unique_id=410000-501-001
    Example: GET /api/compatible/FB03060M
    Example: GET /api/compatible/FB03060M?category=Doors&limit=20
    """
    try:
        child_sku = sku.strip().upper()
        parent_sku = request.args.get('parent_sku', '').strip()
        unique_id = request.args.get('unique_id', '').strip()
        category_filter = request.args.get('category', '').strip()
        limit = request.args.get('limit', type=int, default=100)
        
        logger.info(f"API request for compatible products: child_sku={child_sku}, parent_sku={parent_sku if parent_sku else 'N/A'}, unique_id={unique_id if unique_id else 'N/A'}")
        
        # Create cache key from request parameters
        cache_key = f"{child_sku}|{parent_sku}|{unique_id}|{category_filter}|{limit}"
        
        # Check cache first
        cached_response = get_cached_compatibles(cache_key)
        if cached_response:
            logger.info(f"Cache hit for {cache_key}")
            return jsonify(cached_response)
        
        # Check if database is available
        if not data_loader.check_database_ready():
            logger.error("Database not available")
            return jsonify({
                'success': False,
                'error': 'Database not available',
                'queried_child_sku': child_sku
            }), 503
        
        # Use multi-SKU lookup if parent_sku or unique_id provided
        if parent_sku or unique_id:
            match_result = data_loader.find_product_by_multi_sku(child_sku, parent_sku, unique_id)
            if not match_result:
                return jsonify({
                    'success': False,
                    'error': 'Product not found in database',
                    'queried_child_sku': child_sku,
                    'queried_parent_sku': parent_sku if parent_sku else None,
                    'queried_unique_id': unique_id if unique_id else None,
                    'message': 'No product found matching any of the provided SKUs (child_sku, parent_sku, unique_id)'
                }), 404
            
            product_data = match_result['product_data']
            matched_sku = match_result['matched_sku']
            match_type = match_result['match_type']
            lookup_sku = matched_sku
        else:
            # Fallback to single SKU lookup for backward compatibility
            product_data = data_loader.load_product_from_database(child_sku)
            matched_sku = None
            match_type = None
            lookup_sku = child_sku
            
            # If not found, try stripping variant suffix (e.g., FF03232MD.010 -> FF03232MD)
            if not product_data and '.' in child_sku:
                variant_parent = child_sku.rsplit('.', 1)[0]
                logger.info(f"Product {child_sku} not found, trying variant parent SKU: {variant_parent}")
                product_data = data_loader.load_product_from_database(variant_parent)
                if product_data:
                    lookup_sku = variant_parent
                    matched_sku = variant_parent
                    match_type = 'variant_parent'
            
            if not product_data:
                return jsonify({
                    'success': False,
                    'error': 'Product not found in database',
                    'queried_child_sku': child_sku,
                    'message': 'Product not found. If this is a variant SKU (e.g., SKU.010), the parent SKU may not exist in the database.'
                }), 404
        
        # Load compatibilities from database using the matched SKU
        db_compatibles = data_loader.load_compatible_products_from_database(lookup_sku)
        
        # Check if database results are incomplete (None or only reverse compatibility)
        use_excel_fallback = False
        if db_compatibles is None:
            use_excel_fallback = True
            logger.info(f"Product {lookup_sku} has no compatibilities in database, using Excel fallback")
        else:
            # Count total products across all categories
            total_products = sum(len(products) for products in db_compatibles.values())
            if total_products <= 1:
                # Check if the single product is just a reverse compatibility entry (pointing to itself with score 0)
                for category, products in db_compatibles.items():
                    if len(products) == 1:
                        first_compat = products[0]
                        # If it's pointing to itself with score 0, it's a reverse-only entry
                        if first_compat.get('sku') == lookup_sku and first_compat.get('compatibility_score') == 0:
                            use_excel_fallback = True
                            logger.info(f"Product {lookup_sku} only has reverse compatibility in database (self-reference), using Excel fallback")
                            break
        
        if use_excel_fallback:
            # Fall back to Excel-based compatibility logic (same as web interface)
            logger.info(f"Falling back to Excel data for SKU: {lookup_sku}")
            excel_results = compatibility.find_compatible_products(lookup_sku)
            
            if excel_results and excel_results.get('product'):
                # Helper function to clean NaN values for JSON serialization
                import pandas as pd
                import math
                
                def clean_value(value):
                    """Convert NaN, None, and other invalid JSON values to None"""
                    if value is None:
                        return None
                    if isinstance(value, float) and (pd.isna(value) or math.isnan(value)):
                        return None
                    if pd.isna(value):
                        return None
                    return value
                
                # Convert Excel results to API format
                # The web interface returns {product: {...}, compatibles: [...], incompatibility_reasons: {...}}
                excel_compatibles = excel_results.get('compatibles', [])
                
                compatibles = []
                for item in excel_compatibles:
                    category = item.get('category')
                    products_list = item.get('products', [])
                    
                    if category_filter and category != category_filter:
                        continue
                    
                    limited_products = products_list[:limit] if limit else products_list
                    compatibles.append({
                        'category': category,
                        'products': [{
                            'sku': clean_value(p.get('sku')),
                            'name': clean_value(p.get('name')),
                            'brand': clean_value(p.get('brand')),
                            'category': category,
                            'series': clean_value(p.get('series')),
                            'image_url': clean_value(p.get('image_url')),
                            'product_page_url': clean_value(p.get('product_page_url')),
                            'compatibility_score': p.get('compatibility_score', 500)
                        } for p in limited_products]
                    })
                
                base_product = excel_results['product']
                response = {
                    'success': True,
                    'queried_child_sku': child_sku,
                    'product': {
                        'sku': clean_value(base_product.get('sku')),
                        'name': clean_value(base_product.get('name')),
                        'brand': clean_value(base_product.get('brand')),
                        'category': clean_value(base_product.get('category')),
                        'series': clean_value(base_product.get('series')),
                        'family': clean_value(base_product.get('family')),
                        'image_url': clean_value(base_product.get('image_url')),
                        'product_page_url': clean_value(base_product.get('product_page_url')),
                    },
                    'compatibles': compatibles,
                    'incompatibility_reasons': excel_results.get('incompatibility_reasons', {}),
                    'total_categories': len(compatibles),
                    'data_source': 'excel_fallback',
                    'message': 'Using Excel data (database compatibility not yet computed)'
                }
                if matched_sku:
                    response['matched_sku'] = matched_sku
                    response['match_type'] = match_type
                if parent_sku:
                    response['queried_parent_sku'] = parent_sku
                if unique_id:
                    response['queried_unique_id'] = unique_id
                
                # Cache the response
                cache_compatibles(cache_key, response)
                return jsonify(response)
            else:
                # Excel fallback also found nothing
                logger.warning(f"No compatibility data found in Excel for SKU: {lookup_sku}")
                response = {
                    'success': True,
                    'queried_child_sku': child_sku,
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
                    'compatibles': [],
                    'incompatibility_reasons': {},
                    'total_categories': 0,
                    'data_source': 'none',
                    'message': 'No compatibility data found in database or Excel'
                }
                if matched_sku:
                    response['matched_sku'] = matched_sku
                    response['match_type'] = match_type
                if parent_sku:
                    response['queried_parent_sku'] = parent_sku
                if unique_id:
                    response['queried_unique_id'] = unique_id
                return jsonify(response)
        
        # Build compatibles list
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
            'queried_child_sku': child_sku,
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
        
        # Include SKU matching information
        if matched_sku:
            response['matched_sku'] = matched_sku
            response['match_type'] = match_type
        
        # Include queried SKUs for reference
        if parent_sku:
            response['queried_parent_sku'] = parent_sku
        if unique_id:
            response['queried_unique_id'] = unique_id
        
        # Cache the response before returning
        cache_compatibles(cache_key, response)
        logger.info(f"Cached response for {cache_key}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"API error for compatible/{child_sku}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'queried_child_sku': child_sku
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
# SALSIFY WEBHOOK ENDPOINTS
# ============================================================================

@app.route('/api/salsify/webhook', methods=['POST'])
def salsify_webhook():
    """
    Salsify webhook endpoint for automated data updates.
    
    Salsify sends a POST request when publication completes with:
    {
        "channel_id": "...",
        "channel_name": "...",
        "user_id": "...",
        "publication_status": "completed",
        "product_feed_export_url": "https://s3.amazonaws.com/...",
        "digital_asset_export_url": "..."
    }
    
    Authentication: ?key=<SALSIFY_WEBHOOK_SECRET>
    """
    try:
        webhook_secret = os.environ.get('SALSIFY_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.error("SALSIFY_WEBHOOK_SECRET not configured")
            return jsonify({
                'success': False,
                'error': 'Webhook not configured'
            }), 500
        
        provided_key = request.args.get('key', '')
        if provided_key != webhook_secret:
            logger.warning(f"Invalid webhook key provided from IP: {request.remote_addr}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized'
            }), 401
        
        payload = request.get_json()
        if not payload:
            return jsonify({
                'success': False,
                'error': 'No JSON payload provided'
            }), 400
        
        logger.info(f"Received Salsify webhook: {payload.get('publication_status')}")
        
        publication_status = payload.get('publication_status')
        if publication_status != 'completed':
            logger.info(f"Ignoring webhook with status: {publication_status}")
            return jsonify({
                'success': True,
                'message': f'Ignored status: {publication_status}'
            })
        
        product_feed_url = payload.get('product_feed_export_url')
        if not product_feed_url:
            return jsonify({
                'success': False,
                'error': 'No product_feed_export_url in payload'
            }), 400
        
        from models import get_session, SyncStatus
        session = get_session()
        
        sync_record = SyncStatus(
            sync_type='salsify_webhook',
            status='pending',
            sync_metadata={
                'channel_id': payload.get('channel_id'),
                'channel_name': payload.get('channel_name'),
                'product_feed_url': product_feed_url
            }
        )
        session.add(sync_record)
        session.commit()
        sync_id = sync_record.id
        session.close()
        
        def process_webhook_sync(sync_id, product_feed_url, payload):
            """Background task to process Salsify webhook"""
            # CRITICAL: Threads need Flask app context to access logger, db, etc.
            with app.app_context():
                session = None
                try:
                    # Force early logging to detect thread startup
                    logger.info(f"=== Webhook background thread started for sync #{sync_id} ===")
                    
                    import requests
                    import tempfile
                    from datetime import datetime
                    
                    session = get_session()
                    sync_record = session.query(SyncStatus).filter_by(id=sync_id).first()
                    
                    if not sync_record:
                        logger.error(f"Sync record #{sync_id} not found!")
                        return
                    
                    sync_record.status = 'processing'
                    session.commit()
                    logger.info(f"Sync #{sync_id} status set to processing")
                    
                    logger.info(f"Downloading Excel from Salsify S3: {product_feed_url}")
                    
                    response = requests.get(product_feed_url, timeout=300, stream=True)
                    response.raise_for_status()
                    
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 100 * 1024 * 1024:
                        raise ValueError(f"File too large: {content_length} bytes (max 100MB)")
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        downloaded_size = 0
                        max_size = 100 * 1024 * 1024
                        
                        for chunk in response.iter_content(chunk_size=8192):
                            downloaded_size += len(chunk)
                            if downloaded_size > max_size:
                                raise ValueError(f"Download exceeded max size: {max_size} bytes")
                            tmp_file.write(chunk)
                        
                        temp_path = tmp_file.name
                        logger.info(f"Downloaded Excel file to: {temp_path} ({downloaded_size} bytes)")
                    
                    # Save the downloaded Excel to the main data directory
                    import shutil
                    main_excel_path = os.path.join('data', 'Product Data.xlsx')
                    shutil.copy2(temp_path, main_excel_path)
                    logger.info(f"Saved Excel file to: {main_excel_path}")
                    
                    import db_sync_service
                    sync_result = db_sync_service.full_sync_workflow(temp_path)
                    
                    # Reload the in-memory cache with the new data
                    try:
                        import data_update_service
                        data_update_service.load_data_into_memory(main_excel_path)
                        logger.info("Reloaded in-memory cache with updated product data")
                    except Exception as cache_error:
                        logger.warning(f"Could not reload cache: {cache_error}")
                    
                    os.unlink(temp_path)
                    
                    if sync_result.get('success'):
                        sync_record.status = 'completed'
                        sync_record.completed_at = datetime.utcnow()
                        sync_record.products_added = sync_result.get('products_added', 0)
                        sync_record.products_updated = sync_result.get('products_updated', 0)
                        sync_record.products_deleted = sync_result.get('products_deleted', 0)
                        sync_record.compatibilities_updated = sync_result.get('compatibilities_updated', 0)
                        
                        # Store detailed change information in metadata
                        if sync_record.sync_metadata is None:
                            sync_record.sync_metadata = {}
                        
                        # Merge change_details into existing metadata
                        change_details = sync_result.get('change_details', {})
                        sync_record.sync_metadata['change_details'] = change_details
                        
                        # IMPORTANT: Mark the JSON field as modified so SQLAlchemy saves it
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(sync_record, 'sync_metadata')
                        
                        logger.info(f"Webhook sync completed successfully: {sync_result}")
                        logger.info(f"Saved change details: added={len(change_details.get('added_products', []))}, updated={len(change_details.get('updated_products', []))}, deleted={len(change_details.get('deleted_products', []))}")
                    else:
                        sync_record.status = 'failed'
                        sync_record.completed_at = datetime.utcnow()
                        sync_record.error_message = sync_result.get('error', 'Unknown error')
                        logger.error(f"Webhook sync failed: {sync_result.get('error')}")
                    
                    session.commit()
                    
                except Exception as e:
                    logger.error(f"!!! Error processing webhook sync #{sync_id}: {str(e)} !!!")
                    logger.error(f"!!! Full traceback:\n{traceback.format_exc()} !!!")
                    try:
                        if session and sync_record:
                            sync_record.status = 'failed'
                            sync_record.completed_at = datetime.utcnow()
                            sync_record.error_message = str(e)
                            session.commit()
                            logger.info(f"Sync #{sync_id} marked as failed in database")
                    except Exception as db_error:
                        logger.error(f"!!! Could not update sync status: {db_error} !!!")
                finally:
                    try:
                        if session:
                            session.close()
                            logger.info(f"=== Webhook background thread finished for sync #{sync_id} ===")
                    except Exception as cleanup_error:
                        logger.error(f"!!! Session cleanup error: {cleanup_error} !!!")
        
        webhook_thread = threading.Thread(
            target=process_webhook_sync,
            args=(sync_id, product_feed_url, payload),
            daemon=True  # Daemon threads are fine - they complete quickly (5-10 min)
        )
        webhook_thread.start()
        
        # Note: In production deployment (without --reload), daemon threads work fine.
        # In development with --reload, threads may be killed on worker restart.
        # Add cleanup via /api/salsify/cleanup endpoint if needed.
        
        return jsonify({
            'success': True,
            'message': 'Webhook received and processing started',
            'sync_id': sync_id
        }), 202
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/salsify/status', methods=['GET'])
def salsify_status():
    """
    Get status of Salsify webhook syncs.
    
    Query Parameters:
        - limit: Number of recent syncs to return (default: 10, max: 100)
        - sync_id: Get specific sync by ID
    
    Example: GET /api/salsify/status
    Example: GET /api/salsify/status?sync_id=123
    Example: GET /api/salsify/status?limit=5
    """
    try:
        from models import get_session, SyncStatus
        
        session = get_session()
        
        sync_id = request.args.get('sync_id', type=int)
        if sync_id:
            sync_record = session.query(SyncStatus).filter_by(id=sync_id).first()
            session.close()
            
            if not sync_record:
                return jsonify({
                    'success': False,
                    'error': 'Sync not found'
                }), 404
            
            return jsonify({
                'success': True,
                'sync': {
                    'id': sync_record.id,
                    'sync_type': sync_record.sync_type,
                    'status': sync_record.status,
                    'started_at': sync_record.started_at.isoformat() if sync_record.started_at else None,
                    'completed_at': sync_record.completed_at.isoformat() if sync_record.completed_at else None,
                    'products_added': sync_record.products_added,
                    'products_updated': sync_record.products_updated,
                    'products_deleted': sync_record.products_deleted,
                    'compatibilities_updated': sync_record.compatibilities_updated,
                    'error_message': sync_record.error_message,
                    'metadata': sync_record.sync_metadata
                }
            })
        
        limit = min(request.args.get('limit', type=int, default=10), 100)
        
        recent_syncs = session.query(SyncStatus).order_by(
            SyncStatus.started_at.desc()
        ).limit(limit).all()
        
        syncs_list = []
        for sync in recent_syncs:
            syncs_list.append({
                'id': sync.id,
                'sync_type': sync.sync_type,
                'status': sync.status,
                'started_at': sync.started_at.isoformat() if sync.started_at else None,
                'completed_at': sync.completed_at.isoformat() if sync.completed_at else None,
                'products_added': sync.products_added,
                'products_updated': sync.products_updated,
                'products_deleted': sync.products_deleted,
                'compatibilities_updated': sync.compatibilities_updated,
                'error_message': sync.error_message,
                'metadata': sync.sync_metadata
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'syncs': syncs_list,
            'total_returned': len(syncs_list)
        })
        
    except Exception as e:
        logger.error(f"Status endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/salsify/cleanup', methods=['POST'])
def salsify_cleanup():
    """
    Cleanup stuck webhook syncs that have been in 'processing' status for too long.
    
    This handles cases where background threads were killed due to app restarts.
    
    Query Parameters:
        - hours: Number of hours to consider a sync stuck (default: 2)
    
    Example: POST /api/salsify/cleanup
    Example: POST /api/salsify/cleanup?hours=1
    """
    try:
        from models import get_session, SyncStatus
        from datetime import datetime, timedelta
        
        hours = request.args.get('hours', type=int, default=2)
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        session = get_session()
        
        # Find stuck syncs
        stuck_syncs = session.query(SyncStatus).filter(
            SyncStatus.status == 'processing',
            SyncStatus.started_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        cleaned_ids = []
        
        for sync in stuck_syncs:
            sync.status = 'failed'
            sync.completed_at = datetime.utcnow()
            sync.error_message = f'Sync stuck in processing for >{hours}h - likely killed by app restart (development mode with --reload)'
            cleaned_ids.append(sync.id)
            cleaned_count += 1
        
        if cleaned_count > 0:
            session.commit()
            logger.info(f"Cleaned up {cleaned_count} stuck syncs: {cleaned_ids}")
        
        session.close()
        
        return jsonify({
            'success': True,
            'cleaned_count': cleaned_count,
            'cleaned_sync_ids': cleaned_ids,
            'message': f'Marked {cleaned_count} stuck syncs as failed'
        })
        
    except Exception as e:
        logger.error(f"Cleanup endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# END OF REST API ENDPOINTS
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
