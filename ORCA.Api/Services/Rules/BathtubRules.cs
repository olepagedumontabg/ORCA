using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Rules;

/// <summary>
/// Compatibility rules for bathtubs.
/// Migrated from logic/bathtub_compatibility.py.
/// </summary>
public static class BathtubRules
{
    public static List<CompatibilityCategoryResult> FindCompatibilities(
        Product bathtub,
        List<Product> tubDoors,
        List<Product> tubScreens,
        List<Product> walls)
    {
        var results = new List<CompatibilityCategoryResult>();
        var incompatibilityReasons = new Dictionary<string, string>();

        var attrs = ProductAttributes.Parse(bathtub.Attributes);
        var tubWidth = attrs.GetDecimal("Max Door Width");
        var tubInstall = attrs.GetString("Installation") ?? "";
        var tubSeries = bathtub.Series;
        var tubBrand = bathtub.Brand;
        var tubFamily = bathtub.Family;
        var tubNominal = bathtub.NominalDimensions;
        var tubLength = bathtub.Length;
        var tubWidthActual = bathtub.Width;

        // Check incompatibility reasons
        var doorsCantFit = attrs.GetString("Reason Doors Can't Fit");
        var wallsCantFit = attrs.GetString("Reason Walls Can't Fit");

        if (!string.IsNullOrWhiteSpace(doorsCantFit))
            incompatibilityReasons["Tub Doors"] = doorsCantFit;
        if (!string.IsNullOrWhiteSpace(wallsCantFit))
            incompatibilityReasons["Walls"] = wallsCantFit;

        // ---------- Tub Doors ----------
        if (!incompatibilityReasons.ContainsKey("Tub Doors"))
        {
            var compatibleDoors = new List<CompatibleProductDto>();

            foreach (var door in tubDoors)
            {
                var doorAttrs = ProductAttributes.Parse(door.Attributes);
                var doorMinWidth = doorAttrs.GetDecimal("Minimum Width");
                var doorMaxWidth = doorAttrs.GetDecimal("Maximum Width");
                var doorSeries = door.Series;
                var doorBrand = door.Brand;

                if (string.Equals(tubInstall, "Alcove", StringComparison.OrdinalIgnoreCase)
                    && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, tubWidth)
                    && SharedRules.SeriesCompatible(tubSeries, doorSeries, tubBrand, doorBrand))
                {
                    compatibleDoors.Add(ShowerBaseRules.MapToCompatibleDto(door));
                }
            }

            if (compatibleDoors.Count > 0)
                results.Add(new CompatibilityCategoryResult
                {
                    Category = "Tub Doors",
                    Products = compatibleDoors.OrderBy(d => d.CompatibilityScore ?? 999).ToList()
                });
        }

        // ---------- Tub Screens ----------
        if (!incompatibilityReasons.ContainsKey("Tub Doors"))
        {
            var compatibleScreens = new List<CompatibleProductDto>();

            foreach (var screen in tubScreens)
            {
                var screenAttrs = ProductAttributes.Parse(screen.Attributes);
                var screenPanelWidth = screenAttrs.GetDecimal("Fixed Panel Width");
                var screenSeries = screen.Series;
                var screenBrand = screen.Brand;

                if (string.Equals(tubInstall, "Alcove", StringComparison.OrdinalIgnoreCase)
                    && SharedRules.IsScreenCompatible(tubWidth, screenPanelWidth)
                    && SharedRules.SeriesCompatible(tubSeries, screenSeries, tubBrand, screenBrand))
                {
                    compatibleScreens.Add(ShowerBaseRules.MapToCompatibleDto(screen));
                }
            }

            if (compatibleScreens.Count > 0)
                results.Add(new CompatibilityCategoryResult
                {
                    Category = "Tub Screens",
                    Products = compatibleScreens.OrderBy(s => s.CompatibilityScore ?? 999).ToList()
                });
        }

        // ---------- Walls ----------
        if (!incompatibilityReasons.ContainsKey("Walls"))
        {
            var matchingWalls = ShowerBaseRules.FindCompatibleWalls(
                bathtub, walls,
                tubInstall.ToLowerInvariant(), tubSeries, tubBrand, tubFamily,
                tubNominal, tubLength, tubWidthActual,
                CompatibilityConstants.BathtubUtileFamilies,
                wallTypeFilter: new[] { "tub" },
                installCheck: (wallType) => wallType.Contains("tub"));

            if (matchingWalls.Count > 0)
                results.Add(new CompatibilityCategoryResult
                {
                    Category = "Walls",
                    Products = matchingWalls.OrderBy(w => w.CompatibilityScore ?? 999).ToList()
                });
        }

        // Add incompatibility reasons
        foreach (var (category, reason) in incompatibilityReasons)
        {
            results.Add(new CompatibilityCategoryResult
            {
                Category = category,
                IncompatibilityReason = reason
            });
        }

        // Sort by category order
        var order = CompatibilityConstants.BathtubCategoryOrder;
        results.Sort((a, b) =>
        {
            int ia = Array.IndexOf(order, a.Category);
            int ib = Array.IndexOf(order, b.Category);
            if (ia < 0) ia = order.Length;
            if (ib < 0) ib = order.Length;
            return ia.CompareTo(ib);
        });

        return results;
    }
}
