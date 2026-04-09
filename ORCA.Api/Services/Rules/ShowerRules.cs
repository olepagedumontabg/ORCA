using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Rules;

/// <summary>
/// Compatibility rules for showers (full shower units).
/// Migrated from logic/shower_compatibility.py.
/// Matches shower doors by width AND height, alcove installation only.
/// </summary>
public static class ShowerRules
{
    public static List<CompatibilityCategoryResult> FindCompatibilities(
        Product shower, List<Product> showerDoors)
    {
        var results = new List<CompatibilityCategoryResult>();
        var incompatibilityReasons = new Dictionary<string, string>();

        var attrs = ProductAttributes.Parse(shower.Attributes);
        var showerWidth = attrs.GetDecimal("Max Door Width");
        var showerHeight = attrs.GetDecimal("Max Door Height");
        var showerInstall = attrs.GetString("Installation") ?? "";
        var showerSeries = shower.Series;
        var showerBrand = shower.Brand;

        var doorsCantFit = attrs.GetString("Reason Doors Can't Fit");
        if (!string.IsNullOrWhiteSpace(doorsCantFit))
            incompatibilityReasons["Shower Doors"] = doorsCantFit;

        if (!incompatibilityReasons.ContainsKey("Shower Doors"))
        {
            var compatibleDoors = new List<CompatibleProductDto>();

            foreach (var door in showerDoors)
            {
                var doorAttrs = ProductAttributes.Parse(door.Attributes);
                var doorMinWidth = doorAttrs.GetDecimal("Minimum Width");
                var doorMaxWidth = doorAttrs.GetDecimal("Maximum Width");
                var doorHeight = doorAttrs.GetDecimal("Maximum Height");
                var doorSeries = door.Series;
                var doorBrand = door.Brand;

                if (string.Equals(showerInstall, "Alcove", StringComparison.OrdinalIgnoreCase)
                    && showerWidth.HasValue && showerHeight.HasValue
                    && doorHeight.HasValue
                    && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, showerWidth)
                    && doorHeight.Value <= showerHeight.Value
                    && SharedRules.SeriesCompatible(showerSeries, doorSeries, showerBrand, doorBrand))
                {
                    compatibleDoors.Add(ShowerBaseRules.MapToCompatibleDto(door));
                }
            }

            if (compatibleDoors.Count > 0)
                results.Add(new CompatibilityCategoryResult
                {
                    Category = "Shower Doors",
                    Products = compatibleDoors
                });
        }

        foreach (var (category, reason) in incompatibilityReasons)
        {
            results.Add(new CompatibilityCategoryResult
            {
                Category = category,
                IncompatibilityReason = reason
            });
        }

        return results;
    }
}
