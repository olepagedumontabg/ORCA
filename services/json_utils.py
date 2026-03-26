"""
JSON serialization utilities for handling NaN/None values from pandas data.
"""

import json
import pandas as pd


def clean_value(value):
    """Convert NaN, None, and other invalid JSON values to None."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def deep_clean(obj):
    """Recursively clean NaN and problematic values from a nested structure."""
    if isinstance(obj, (list, tuple)):
        return [deep_clean(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: deep_clean(v) for k, v in obj.items()}
    elif obj is None:
        return None
    elif isinstance(obj, float) and pd.isna(obj):
        return None
    else:
        return obj


def json_default(obj):
    """Custom JSON encoder fallback for non-standard types."""
    if pd.isna(obj) if hasattr(pd, 'isna') else False:
        return None
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif isinstance(obj, (complex, bytes, bytearray)):
        return str(obj)
    return str(obj)


def safe_jsonify_data(data):
    """Clean and serialize data safely for JSON response.

    Returns a dict that is safe to pass to flask.jsonify().
    """
    cleaned = deep_clean(data)
    json_str = json.dumps(cleaned, default=json_default)
    return json.loads(json_str)
