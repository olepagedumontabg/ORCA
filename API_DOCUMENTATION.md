# Bathroom Compatibility Finder - REST API Documentation

## Overview

The Bathroom Compatibility Finder provides a REST API for accessing product data and compatibility information. This API allows external applications to query product catalogs and find compatible bathroom products.

**Base URL**: `https://your-replit-url.replit.app` or `http://localhost:5000` (development)

**Authentication**: No authentication required (add authentication if needed in production)

**Response Format**: JSON

---

## Endpoints

### 1. Health Check

Get system status and data freshness information.

**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "success": true,
  "status": "healthy",
  "total_products": 2194,
  "categories": 11,
  "data_service_available": true,
  "last_data_update": "2025-10-22T15:32:24.423609"
}
```

**Example**:
```bash
curl https://your-app.replit.app/api/health
```

---

### 2. List Categories

Get all available product categories with counts.

**Endpoint**: `GET /api/categories`

**Response**:
```json
{
  "success": true,
  "categories": [
    {
      "name": "Shower Bases",
      "product_count": 442
    },
    {
      "name": "Bathtubs",
      "product_count": 241
    },
    {
      "name": "Shower Doors",
      "product_count": 883
    }
  ],
  "total_categories": 11
}
```

**Example**:
```bash
curl https://your-app.replit.app/api/categories
```

---

### 3. Get Product Details

Get detailed information about a specific product by SKU.

**Endpoint**: `GET /api/product/<sku>`

**Parameters**:
- `sku` (path parameter): Product SKU (e.g., "FB03060M")

**Response**:
```json
{
  "success": true,
  "sku": "FB03060M",
  "category": "Shower Bases",
  "product": {
    "Brand": "Swan",
    "Family": "Veritek™",
    "Image URL": "https://...",
    "Installation": "Alcove",
    "Length": 60.0,
    "Max Door Width": 58.25,
    "Nominal Dimensions": "60 x 30",
    "Product Name": "FBF-3060LM/RM",
    "Product Page URL": "https://swanstone.com/",
    "Series": null,
    "Unique ID": "FB03060M",
    "Width": 30.0
  }
}
```

**Error Response** (404):
```json
{
  "success": false,
  "error": "Product not found",
  "sku": "INVALID_SKU"
}
```

**Example**:
```bash
curl https://your-app.replit.app/api/product/FB03060M
```

---

### 4. Get Compatible Products

Get all products compatible with a specific SKU. Supports multi-SKU lookup with priority matching for applications using different SKU formats.

**Endpoint**: `GET /api/compatible/<child_sku>`

**Parameters**:
- `child_sku` (path parameter): Your application's product SKU (highest priority)
- `parent_sku` (query parameter, optional): Parent SKU for compatibility lookup (medium priority)
- `unique_id` (query parameter, optional): Unique product ID (lowest priority)
- `category` (query parameter, optional): Filter results by category (e.g., "Shower Doors", "Walls")
- `brand` (query parameter, optional): Filter results by brand name (case-insensitive, e.g., "MAAX", "Neptune")
- `limit` (query parameter, optional): Limit results per category (default: 100)

**Multi-SKU Lookup Priority**:
The system searches for a product match in the following order:
1. **child_sku** (path parameter) - Checked first
2. **parent_sku** (query parameter) - Checked if child_sku not found
3. **unique_id** (query parameter) - Checked if parent_sku not found

This allows your application to pass all available SKU formats and get the best match.

**Response**:
```json
{
  "success": true,
  "queried_child_sku": "410000-501-001-000",
  "queried_parent_sku": "410000",
  "queried_unique_id": "410000-501-001",
  "matched_sku": "410000-501-001",
  "match_type": "unique_id",
  "product": {
    "brand": "Maax",
    "category": "Shower Bases",
    "family": "B3",
    "image_url": "https://...",
    "name": "B3Round 6032 - Tunnel",
    "sku": "410000-501-001"
  },
  "compatibles": [
    {
      "category": "Shower Doors",
      "products": [
        {
          "brand": "DreamLine",
          "category": "Shower Doors",
          "sku": "139584",
          "name": "Capella 78 32 ½-35 ½ x 78",
          "glass_thickness": "8mm",
          "door_type": "Pivot",
          "compatibility_score": 95,
          "product_page_url": "https://...",
          "image_url": "https://..."
        }
      ]
    },
    {
      "category": "Walls",
      "products": [
        {
          "brand": "Maax",
          "category": "Walls",
          "sku": "107479",
          "name": "Utile 3636 Shower Wall Kit",
          "compatibility_score": 98
        }
      ]
    }
  ],
  "incompatibility_reasons": {},
  "total_categories": 2,
  "data_source": "database"
}
```

**Examples**:
```bash
# Multi-SKU lookup (recommended for external applications)
curl "https://your-app.replit.app/api/compatible/410000-501-001-000?parent_sku=410000&unique_id=410000-501-001"

# Single SKU lookup (backward compatible)
curl https://your-app.replit.app/api/compatible/FB03060M

# Filter compatible doors only
curl "https://your-app.replit.app/api/compatible/FB03060M?category=Shower%20Doors"

# Filter by brand - only show MAAX compatible products
curl "https://your-app.replit.app/api/compatible/FB03060M?brand=MAAX"

# Combine filters - only MAAX walls
curl "https://your-app.replit.app/api/compatible/FB03060M?brand=MAAX&category=Walls"

# Filter by brand with limit
curl "https://your-app.replit.app/api/compatible/FB03060M?brand=Neptune&limit=10"

# Limit results to 5 per category
curl "https://your-app.replit.app/api/compatible/FB03060M?limit=5"
```

**Response Fields**:
- `queried_child_sku`: The child SKU you provided in the request
- `queried_parent_sku`: The parent SKU you provided (if any)
- `queried_unique_id`: The unique ID you provided (if any)
- `matched_sku`: Which SKU was found in the database
- `match_type`: Which SKU type matched (`child_sku`, `parent_sku`, `unique_id`, or `variant_parent`)
- `product`: Base product details
- `compatibles`: Array of compatible product categories
  - `category`: Product category name
  - `products`: Array of compatible products
    - `glass_thickness`: Glass thickness for doors (e.g., "8mm")
    - `door_type`: Door type for doors (e.g., "Pivot", "Sliding")
    - `compatibility_score`: Numerical score (0-100)
  - `total_count`: Total number of compatible products in this category (if truncated)
  - `truncated`: True if results were limited
- `incompatibility_reasons`: Reasons why certain categories have no matches
- `total_categories`: Total number of categories with compatible products
- `data_source`: Data source used (`database` or `excel`)

---

### 5. List All Products

Get a paginated list of all products with optional filtering.

**Endpoint**: `GET /api/products`

**Query Parameters**:
- `category` (optional): Filter by category name
- `brand` (optional): Filter by brand name
- `limit` (optional): Number of results to return (default: 100, max: 1000)
- `offset` (optional): Number of results to skip (default: 0)

**Response**:
```json
{
  "success": true,
  "products": [
    {
      "category": "Shower Bases",
      "Unique ID": "FB03060M",
      "Product Name": "FBF-3060LM/RM",
      "Brand": "Swan",
      "Series": null,
      "Family": "Veritek™",
      "Length": 60.0,
      "Width": 30.0,
      "Product Page URL": "https://swanstone.com/",
      "Image URL": "https://..."
    }
  ],
  "total_count": 442,
  "limit": 100,
  "offset": 0,
  "returned_count": 100
}
```

**Examples**:
```bash
# Get first 100 products
curl https://your-app.replit.app/api/products

# Get Swan shower bases only
curl "https://your-app.replit.app/api/products?category=Shower%20Bases&brand=Swan"

# Pagination: Get next 100 products
curl "https://your-app.replit.app/api/products?limit=100&offset=100"

# Get all bathtubs (up to 1000)
curl "https://your-app.replit.app/api/products?category=Bathtubs&limit=1000"
```

---

## Data Models

### Product Object

```json
{
  "Unique ID": "string",           // Product SKU
  "Product Name": "string",         // Product display name
  "Brand": "string",                // Product brand
  "Series": "string|null",          // Product series
  "Family": "string|null",          // Product family
  "Length": "number|null",          // Product length in inches
  "Width": "number|null",           // Product width in inches
  "Height": "number|null",          // Product height in inches
  "Nominal Dimensions": "string",   // Human-readable dimensions
  "Product Page URL": "string",     // Product webpage
  "Image URL": "string",            // Product image
  "Ranking": "number|null",         // Internal ranking score
  // ... additional category-specific attributes
}
```

### Compatible Product Object

```json
{
  "sku": "string",                  // Product SKU
  "name": "string",                 // Product name
  "brand": "string",                // Product brand
  "series": "string|null",          // Product series
  "category": "string",             // Product category
  "product_page_url": "string",     // Product webpage
  "image_url": "string",            // Product image
  "compatibility_score": "number",  // Compatibility score (0-100)
  "glass_thickness": "string",      // Glass thickness (doors only, e.g., "8mm")
  "door_type": "string"             // Door type (doors only, e.g., "Pivot")
}
```

---

## Error Handling

All endpoints return errors in a consistent format:

**Error Response**:
```json
{
  "success": false,
  "error": "Error description",
  "sku": "FB03060M"  // Included when relevant
}
```

**HTTP Status Codes**:
- `200 OK`: Success
- `404 Not Found`: Product or resource not found
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Currently, no rate limiting is enforced. For production use, consider implementing:
- Rate limiting per IP address
- API keys for authentication
- Usage quotas

---

## Integration Examples

### Python

```python
import requests

# Get compatible products
response = requests.get(
    'https://your-app.replit.app/api/compatible/FB03060M',
    params={'limit': 20}
)
data = response.json()

if data['success']:
    print(f"Found {data['total_categories']} compatible categories")
    for category in data['compatibles']:
        print(f"  {category['category']}: {len(category['products'])} products")
```

### JavaScript/Node.js

```javascript
// Get product details
const response = await fetch(
  'https://your-app.replit.app/api/product/FB03060M'
);
const data = await response.json();

if (data.success) {
  console.log(`Product: ${data.product['Product Name']}`);
  console.log(`Category: ${data.category}`);
}
```

### cURL

```bash
# Get health status
curl https://your-app.replit.app/api/health

# Get compatible products with pretty printing
curl -s "https://your-app.replit.app/api/compatible/FB03060M?limit=5" | jq .

# Get all categories
curl -s https://your-app.replit.app/api/categories | jq '.categories[] | .name'
```

---

## Data Source

The API uses a **hybrid data source approach**:

1. **Primary Source**: PostgreSQL database (when available)
   - Fast queries (< 50ms)
   - Pre-computed compatibility matches
   - Optimized for high-volume access

2. **Fallback Source**: Excel files
   - Real-time compatibility computation
   - Always up-to-date with FTP sync
   - Used when database is unavailable or being populated

Check the `/api/health` endpoint to see which data source is currently active.

---

## Best Practices

1. **Cache Results**: Product data updates daily, so cache API responses for better performance
2. **Handle Errors**: Always check the `success` field in responses
3. **Pagination**: Use `limit` and `offset` for large result sets
4. **Specific Queries**: Filter by category and brand to reduce response sizes
5. **Monitor Health**: Periodically check `/api/health` for system status

---

## Support

For issues or questions about the API:
- Check the `/api/health` endpoint for system status
- Review incompatibility reasons in `/api/compatible` responses
- Contact the development team for support

---

## Changelog

### November 17, 2025
- Added `brand` filter parameter to `/api/compatible/<sku>` endpoint
- Allows filtering compatible products by brand name (case-insensitive)
- Can be combined with existing `category` filter

### November 2025
- Added Salsify webhook integration endpoints
- Added `/api/salsify/webhook` for automated data updates
- Added `/api/salsify/status` for sync monitoring
- Improved webhook reliability with automatic recovery from crashes

### October 22, 2025
- Initial API release
- Added 5 REST endpoints
- Implemented hybrid data source (database + Excel fallback)
- Added pagination and filtering support
