using ORCA.Api.Domain.Constants;

namespace ORCA.Api.Services.Rules;

/// <summary>
/// Centralized compatibility rules used across all product category modules.
/// Migrated from logic/shared_rules.py.
/// </summary>
public static class SharedRules
{
    /// <summary>
    /// Check if two series are compatible.
    /// Series restrictions have been removed - all series are now compatible.
    /// Kept for backward compatibility and future extensibility.
    /// </summary>
    public static bool SeriesCompatible(string? baseSeries, string? compareSeries,
        string? baseBrand = null, string? compareBrand = null)
    {
        return true;
    }

    /// <summary>
    /// Check if two product families are compatible based on business rules.
    ///
    /// Rules:
    /// - Exclusive families (olio, vellamo, interflo, w&amp;b) only match themselves.
    /// - Utile/Nextile walls only match specific base families (differs by product type).
    /// - All other combinations are compatible.
    /// </summary>
    public static bool BrandFamilyMatch(string? baseFamily, string? wallFamily,
        HashSet<string>? allowedUtileFamilies = null)
    {
        var baseFam = (baseFamily ?? "").Trim().ToLowerInvariant();
        var wallFam = (wallFamily ?? "").Trim().ToLowerInvariant();

        allowedUtileFamilies ??= CompatibilityConstants.ShowerBaseUtileFamilies;

        // Exclusive families: must match exactly
        foreach (var exclusive in CompatibilityConstants.ExclusiveFamilies)
        {
            if (string.Equals(baseFam, exclusive, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(wallFam, exclusive, StringComparison.OrdinalIgnoreCase))
                return false;

            if (string.Equals(wallFam, exclusive, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(baseFam, exclusive, StringComparison.OrdinalIgnoreCase))
                return false;
        }

        // Utile/Nextile walls only match with specific base families
        if ((string.Equals(wallFam, "utile", StringComparison.OrdinalIgnoreCase)
             || string.Equals(wallFam, "nextile", StringComparison.OrdinalIgnoreCase))
            && !allowedUtileFamilies.Contains(baseFam))
        {
            return false;
        }

        return true;
    }

    /// <summary>
    /// Check if a fixture (base or bathtub) is wide enough for a screen.
    /// The gap between fixture width and screen panel width must exceed ScreenMinGap (22 inches).
    /// </summary>
    public static bool IsScreenCompatible(decimal? fixtureWidth, decimal? screenPanelWidth)
    {
        if (!fixtureWidth.HasValue || !screenPanelWidth.HasValue)
            return false;

        return fixtureWidth.Value - screenPanelWidth.Value > CompatibilityConstants.ScreenMinGap;
    }

    /// <summary>
    /// Check if a fixture width falls within a door's width range.
    /// </summary>
    public static bool DoorWidthFits(decimal? doorMinWidth, decimal? doorMaxWidth, decimal? fixtureWidth)
    {
        if (!fixtureWidth.HasValue || !doorMinWidth.HasValue || !doorMaxWidth.HasValue)
            return false;

        return doorMinWidth.Value <= fixtureWidth.Value && fixtureWidth.Value <= doorMaxWidth.Value;
    }

    /// <summary>
    /// Check if a shower base's dimensions match an enclosure within tolerance.
    /// The base must be at least as large as the enclosure opening, but not exceed it by more than the tolerance.
    /// </summary>
    public static bool EnclosureDimensionsMatch(decimal? baseLength, decimal? baseWidth,
        decimal? encDoorWidth, decimal? encReturnWidth, decimal tolerance = 2.0m)
    {
        if (!baseLength.HasValue || !baseWidth.HasValue
            || !encDoorWidth.HasValue || !encReturnWidth.HasValue)
            return false;

        var bl = baseLength.Value;
        var bw = baseWidth.Value;
        var edw = encDoorWidth.Value;
        var erw = encReturnWidth.Value;

        return bl >= edw && (bl - edw) <= tolerance
            && bw >= erw && (bw - erw) <= tolerance;
    }
}
