"""
Shared Business Rules for Product Compatibility

Centralized compatibility rules used across all product category modules.
This module eliminates duplication of series_compatible(), brand_family_match(),
screen compatibility checks, door width checks, and enclosure tolerance checks.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Families that are exclusive (only compatible with themselves)
EXCLUSIVE_FAMILIES = {"olio", "vellamo", "interflo", "w&b"}

# Families allowed for Utile/Nextile walls when matched with shower bases
SHOWER_BASE_UTILE_FAMILIES = {
    "b3", "finesse", "distinct", "zone", "olympia", "icon", "roka", "stonea"
}

# Families allowed for Utile/Nextile walls when matched with bathtubs
BATHTUB_UTILE_FAMILIES = {
    "nomad", "mackenzie", "exhibit", "new town", "rubix",
    "bosca", "cocoon", "corinthia"
}

# Minimum gap required between fixture width and screen panel width (inches)
SCREEN_MIN_GAP = 22


def series_compatible(base_series, compare_series, base_brand=None, compare_brand=None):
    """
    Check if two series are compatible based on business rules.

    NOTE: Series rules have been removed - all series are now compatible.
    This function is kept for backward compatibility but always returns True.

    Args:
        base_series: Series of the base product
        compare_series: Series of the product to compare with
        base_brand: Brand of the base product (optional, unused)
        compare_brand: Brand of the compare product (optional, unused)

    Returns:
        bool: Always returns True (series restrictions removed)
    """
    return True


def brand_family_match(base_family, wall_family, allowed_utile_families=None):
    """
    Check if two product families are compatible based on business rules.

    Rules:
    - Exclusive families (olio, vellamo, interflo, w&b) only match themselves.
    - Utile/Nextile walls only match specific base families (differs by product type).
    - All other combinations are compatible.

    Args:
        base_family: Family of the base product (shower base or bathtub)
        wall_family: Family of the wall/accessory product
        allowed_utile_families: Set of families allowed to match with utile/nextile.
            Use SHOWER_BASE_UTILE_FAMILIES or BATHTUB_UTILE_FAMILIES.
            If None, defaults to SHOWER_BASE_UTILE_FAMILIES.

    Returns:
        bool: True if families are compatible, False otherwise
    """
    base_family = str(base_family).strip().lower() if base_family else ""
    wall_family = str(wall_family).strip().lower() if wall_family else ""

    if allowed_utile_families is None:
        allowed_utile_families = SHOWER_BASE_UTILE_FAMILIES

    # Exclusive families: must match exactly
    for exclusive in EXCLUSIVE_FAMILIES:
        if base_family == exclusive and wall_family != exclusive:
            return False
        if wall_family == exclusive and base_family != exclusive:
            return False

    # Utile/Nextile walls only match with specific base families
    if wall_family in ("utile", "nextile") and base_family not in allowed_utile_families:
        return False

    return True


def is_screen_compatible(fixture_width, screen_panel_width):
    """
    Check if a fixture (base or bathtub) is wide enough for a screen.

    The gap between fixture width and screen panel width must exceed
    SCREEN_MIN_GAP (22 inches).

    Args:
        fixture_width: Max door width of the fixture (base or bathtub)
        screen_panel_width: Fixed panel width of the screen

    Returns:
        bool: True if the gap is sufficient, False otherwise
    """
    if pd.isna(fixture_width) or pd.isna(screen_panel_width):
        return False
    try:
        return float(fixture_width) - float(screen_panel_width) > SCREEN_MIN_GAP
    except (ValueError, TypeError):
        return False


def door_width_fits(door_min_width, door_max_width, fixture_width):
    """
    Check if a fixture width falls within a door's width range.

    Args:
        door_min_width: Minimum width the door can fit
        door_max_width: Maximum width the door can fit
        fixture_width: Width of the fixture (base, bathtub, shower, etc.)

    Returns:
        bool: True if fixture width is within door range
    """
    if pd.isna(fixture_width) or pd.isna(door_min_width) or pd.isna(door_max_width):
        return False
    try:
        fw = float(fixture_width)
        return float(door_min_width) <= fw <= float(door_max_width)
    except (ValueError, TypeError):
        return False


def enclosure_dimensions_match(base_length, base_width, enc_door_width, enc_return_width, tolerance=2.0):
    """
    Check if a shower base's dimensions match an enclosure within tolerance.

    The base must be at least as large as the enclosure opening, but not
    exceed it by more than the tolerance.

    Args:
        base_length: Length of the shower base
        base_width: Width of the shower base
        enc_door_width: Door width of the enclosure
        enc_return_width: Return panel width of the enclosure
        tolerance: Maximum allowed overhang in inches (2.0 for forward, 3.0 for reverse)

    Returns:
        bool: True if dimensions match within tolerance
    """
    if any(pd.isna(v) for v in [base_length, base_width, enc_door_width, enc_return_width]):
        return False
    try:
        bl = float(base_length)
        bw = float(base_width)
        edw = float(enc_door_width)
        erw = float(enc_return_width)
        return (
            bl >= edw and (bl - edw) <= tolerance and
            bw >= erw and (bw - erw) <= tolerance
        )
    except (ValueError, TypeError):
        return False
