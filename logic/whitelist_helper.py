import os, logging
import pandas as pd

logger = logging.getLogger(__name__)

_WHITELIST_CACHE = None
WHITELIST_FILE = "compatibility_whitelist.xlsx"  # or .csv


def _load_whitelist() -> set[frozenset]:
    """Lazy‑load the whitelist into a set of frozensets for fast lookup."""
    global _WHITELIST_CACHE
    if _WHITELIST_CACHE is not None:
        return _WHITELIST_CACHE

    path = os.path.join(os.path.dirname(__file__), "..", "data", WHITELIST_FILE)
    pairs: set[frozenset] = set()
    if os.path.exists(path):
        try:
            df = pd.read_excel(path) if path.endswith(".xlsx") else pd.read_csv(path)
            col1, col2 = df.columns[:2]
            for _, row in df.iterrows():
                a = str(row[col1]).strip().upper()
                b = str(row[col2]).strip().upper()
                if a and b and a != "NAN" and b != "NAN":
                    pairs.add(frozenset((a, b)))
            logger.info("Loaded %d whitelist pairs", len(pairs))
        except Exception as exc:
            logger.error("Error loading whitelist: %s", exc)

    _WHITELIST_CACHE = pairs
    return pairs


def get_whitelist_for_sku(sku: str) -> list[str]:
    """Return the list of SKUs explicitly whitelisted with *sku*."""
    sku = sku.strip().upper()
    return [
        list(pair - {sku})[0]        # the 'other' SKU in the pair
        for pair in _load_whitelist()
        if sku in pair
    ]