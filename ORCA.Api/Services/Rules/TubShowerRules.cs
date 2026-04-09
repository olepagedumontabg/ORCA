using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Rules;

/// <summary>
/// Compatibility rules for tub/shower combo units.
/// Migrated from logic/tubshower_compatibility.py.
/// Matches tub doors by width AND height (no installation type restriction).
/// </summary>
public static class TubShowerRules
{
    public static List<CompatibilityCategoryResult> FindCompatibilities(
        Product tubShower, List<Product> tubDoors)
    {
        var results = new List<CompatibilityCategoryResult>();
        var incompatibilityReasons = new Dictionary<string, string>();

        var attrs = ProductAttributes.Parse(tubShower.Attributes);
        var tubWidth = attrs.GetDecimal("Max Door Width");
        var tubHeight = attrs.GetDecimal("Max Door Height");
        var tubSeries = tubShower.Series;
        var tubBrand = tubShower.Brand;

        var doorsCantFit = attrs.GetString("Reason Doors Can't Fit");
        if (!string.IsNullOrWhiteSpace(doorsCantFit))
            incompatibilityReasons["Tub Doors"] = doorsCantFit;

        if (!incompatibilityReasons.ContainsKey("Tub Doors"))
        {
            var compatibleDoors = new List<CompatibleProductDto>();

            foreach (var door in tubDoors)
            {
                var doorAttrs = ProductAttributes.Parse(door.Attributes);
                var doorMinWidth = doorAttrs.GetDecimal("Minimum Width");
                var doorMaxWidth = doorAttrs.GetDecimal("Maximum Width");
                var doorHeight = doorAttrs.GetDecimal("Maximum Height");
                var doorSeries = door.Series;
                var doorBrand = door.Brand;

                if (tubWidth.HasValue && tubHeight.HasValue
                    && doorHeight.HasValue
                    && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, tubWidth)
                    && doorHeight.Value <= tubHeight.Value
                    && SharedRules.SeriesCompatible(tubSeries, doorSeries, tubBrand, doorBrand))
                {
                    compatibleDoors.Add(ShowerBaseRules.MapToCompatibleDto(door));
                }
            }

            if (compatibleDoors.Count > 0)
                results.Add(new CompatibilityCategoryResult
                {
                    Category = "Tub Doors",
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
