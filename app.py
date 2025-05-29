import os
import logging
import threading
from flask import Flask, render_template, request, jsonify, send_file, abort
import pandas as pd
import io
import traceback
from logic import compatibility

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
            target=data_service.run_data_service,
            daemon=True
        )
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
    Return an .xlsx workbook of the same data the UI shows for <sku>.
    Sheet 1  → searched product (1 row)  
    Sheet 2+ → one sheet per compatibility category.
    """
    result = compatibility.find_compatible_products(sku)
    if result["product"] is None:
        return abort(404, "SKU not found")

    # --- Build an in‑memory Excel workbook ---------------------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as xl:
        # Sheet 1 – source product
        pd.DataFrame([result["product"]]).to_excel(
            xl, sheet_name="Source Product", index=False
        )

        # One sheet per category
        for cat in result["compatibles"]:
            df = pd.DataFrame(cat["products"])
            # Drop helper fields the UI uses but the user doesn’t need
            df = df.drop(columns=[col for col in df.columns if col.startswith("_")], errors="ignore")
            df.to_excel(xl, sheet_name=cat["category"][:31], index=False)  # Excel sheet max = 31 chars

    output.seek(0)
    filename = f"compatibilities_{sku}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
                    product_name = str(row[product_name_col]) if product_name_col else ''
                    sku_product_map[sku] = product_name

        # Find matches by SKU
        matching_skus_by_id = [sku for sku in sku_product_map.keys() if query in sku]

        # Find matches by product name
        matching_skus_by_name = []
        for sku, product_name in sku_product_map.items():
            if product_name and query in product_name.upper():
                matching_skus_by_name.append(sku)

        # Combine unique matches, prioritizing SKU matches
        matching_skus = list(dict.fromkeys(matching_skus_by_id + matching_skus_by_name))

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
        logger.debug(f"Found {len(matching_skus)} suggestions for query '{query}' (SKU: {len(matching_skus_by_id)}, Name: {len(matching_skus_by_name)})")

        return jsonify({
            'suggestions': matching_skus,  # Original SKUs for selection
            'displaySuggestions': display_suggestions  # Formatted display strings
        })

    except Exception as e:
        logger.error(f"Error in suggest_skus: {str(e)}")
        return jsonify({'suggestions': [], 'displaySuggestions': [], 'error': str(e)})

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