import os, logging
import pandas as pd

logger = logging.getLogger(__name__)

# Path is relative to the /data folder next to your Excel workbooks
BLACKLIST_FILE = "compatibility_blacklist.xlsx"
_blacklist_cache = None     # Lazy‑loaded singleton


def _load_blacklist():
    """Read the Excel/CSV blacklist into a set[frozenset] once."""
    global _blacklist_cache
    if _blacklist_cache is not None:
        return _blacklist_cache

    blacklist_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", BLACKLIST_FILE
    )
    cache = set()
    if os.path.exists(blacklist_path):
        try:
            df = pd.read_excel(blacklist_path) if blacklist_path.endswith(".xlsx") \
                 else pd.read_csv(blacklist_path)

            # Expect at least two columns
            col1, col2 = df.columns[:2]
            for _, row in df.iterrows():
                sku_a = str(row[col1]).strip().upper()
                sku_b = str(row[col2]).strip().upper()
                if sku_a and sku_b and sku_a != "NAN" and sku_b != "NAN":
                    cache.add(frozenset((sku_a, sku_b)))
            logger.info(f"Loaded {len(cache)} blacklist pairs")
        except Exception as exc:
            logger.error(f"Error loading compatibility blacklist: {exc}")

    _blacklist_cache = cache
    return cache


def is_blacklisted(sku_a: str, sku_b: str) -> bool:
    """True if sku_a / sku_b is in the blacklist (case‑insensitive, order‑agnostic)."""
    if not sku_a or not sku_b:
        return False
    bl = _load_blacklist()
    return frozenset((sku_a.strip().upper(), sku_b.strip().upper())) in bl
