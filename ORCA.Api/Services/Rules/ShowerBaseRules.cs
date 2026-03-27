using System.Text.Json;
using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Rules;

/// <summary>
/// Compatibility rules for shower bases.
/// Migrated from logic/base_compatibility.py.
/// </summary>
public static class ShowerBaseRules
{
    public static List<CompatibilityCategoryResult> FindCompatibilities(
        Product baseProduct,
        List<Product> showerDoors,
        List<Product> returnPanels,
        List<Product> enclosures,
        List<Product> showerScreens,
        List<Product> walls)
    {
        var results = new List<CompatibilityCategoryResult>();
        var incompatibilityReasons = new Dictionary<string, string>();

        var baseAttrs = ProductAttributes.Parse(baseProduct.Attributes);
        var baseWidth = baseAttrs.GetDecimal("Max Door Width");
        var baseInstall = (baseAttrs.GetString("Installation") ?? "").ToLowerInvariant();
        var baseSeries = baseProduct.Series;
        var baseBrand = baseProduct.Brand;
        var baseFamily = baseProduct.Family;
        var baseFitReturn = baseAttrs.GetString("Fits Return Panel Size");
        var baseLength = baseProduct.Length;
        var baseWidthActual = baseProduct.Width;
        var baseNominal = baseProduct.NominalDimensions;

        // Check incompatibility reasons
        var doorsCantFit = baseAttrs.GetString("Reason Doors Can't Fit");
        var wallsCantFit = baseAttrs.GetString("Reason Walls Can't Fit");

        if (!string.IsNullOrWhiteSpace(doorsCantFit))
            incompatibilityReasons["Shower Doors"] = doorsCantFit;
        if (!string.IsNullOrWhiteSpace(wallsCantFit))
            incompatibilityReasons["Walls"] = wallsCantFit;

        // ---------- Doors ----------
        var allDoors = new List<CompatibleProductDto>();
        var allReturnPanels = new List<CompatibleProductDto>();

        if (!incompatibilityReasons.ContainsKey("Shower Doors"))
        {
            var alcoveDoors = new List<CompatibleProductDto>();
            var matchingDoors = new List<CompatibleProductDto>();
            var cornerDoors = new List<(CompatibleProductDto Door, CompatibleProductDto Panel)>();

            foreach (var door in showerDoors)
            {
                var doorAttrs = ProductAttributes.Parse(door.Attributes);
                var doorMinWidth = doorAttrs.GetDecimal("Minimum Width");
                var doorMaxWidth = doorAttrs.GetDecimal("Maximum Width");
                var doorHasReturn = doorAttrs.GetString("Has Return Panel");
                var doorFamily = door.Family;
                var doorSeries = door.Series;
                var doorBrand = door.Brand;

                // Alcove match
                bool alcoveMatch = baseInstall.Contains("alcove")
                    && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, baseWidth)
                    && SharedRules.SeriesCompatible(baseSeries, doorSeries, baseBrand, doorBrand);

                if (alcoveMatch)
                {
                    var doorDto = MapToCompatibleDto(door);
                    if (baseInstall.Contains("alcove") && baseInstall.Contains("corner"))
                        alcoveDoors.Add(doorDto);
                    else
                        matchingDoors.Add(doorDto);
                }

                // Corner match with return panel
                bool cornerDoorCompatible = baseInstall.Contains("corner")
                    && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, baseWidth)
                    && SharedRules.SeriesCompatible(baseSeries, doorSeries, baseBrand, doorBrand);

                if (cornerDoorCompatible)
                {
                    bool isPureCorner = baseInstall.Contains("corner") && !baseInstall.Contains("alcove");

                    foreach (var panel in returnPanels)
                    {
                        var panelAttrs = ProductAttributes.Parse(panel.Attributes);
                        var panelSize = panelAttrs.GetString("Return Panel Size");
                        var panelFamily = panel.Family;

                        bool exactMatch = !string.IsNullOrEmpty(baseFitReturn)
                            && !string.IsNullOrEmpty(panelSize)
                            && baseFitReturn == panelSize
                            && string.Equals(doorFamily, panelFamily, StringComparison.OrdinalIgnoreCase);

                        bool familyCompatible = isPureCorner || string.Equals(doorFamily, panelFamily, StringComparison.OrdinalIgnoreCase);
                        bool fallbackMatch = string.IsNullOrEmpty(baseFitReturn)
                            && baseInstall.Contains("corner")
                            && familyCompatible;

                        if (exactMatch || fallbackMatch)
                        {
                            cornerDoors.Add((MapToCompatibleDto(door), MapToCompatibleDto(panel)));
                        }
                    }
                }
            }

            // Consolidate all doors
            allDoors.AddRange(alcoveDoors);
            allDoors.AddRange(matchingDoors);

            foreach (var (door, panel) in cornerDoors)
            {
                allDoors.Add(door);
                allReturnPanels.Add(panel);
            }

            // Deduplicate by SKU
            allDoors = allDoors.GroupBy(d => d.Sku).Select(g => g.First()).ToList();
            allReturnPanels = allReturnPanels.GroupBy(p => p.Sku).Select(g => g.First()).ToList();

            if (allDoors.Count > 0)
                results.Add(new CompatibilityCategoryResult { Category = "Shower Doors", Products = SortByRanking(allDoors) });
            if (allReturnPanels.Count > 0)
                results.Add(new CompatibilityCategoryResult { Category = "Return Panels", Products = SortByRanking(allReturnPanels) });
        }

        // ---------- Enclosures ----------
        if (baseInstall.Contains("corner") && !incompatibilityReasons.ContainsKey("Shower Doors"))
        {
            var matchingEnclosures = new List<CompatibleProductDto>();
            const decimal tolerance = 2.0m;

            foreach (var enc in enclosures)
            {
                var encAttrs = ProductAttributes.Parse(enc.Attributes);
                var encSeries = enc.Series;
                var encBrand = enc.Brand;
                var encNominal = enc.NominalDimensions;
                var encDoorWidth = encAttrs.GetDecimal("Door Width");
                var encReturnWidth = encAttrs.GetDecimal("Return Panel Width");

                if (!SharedRules.SeriesCompatible(baseSeries, encSeries, baseBrand, encBrand))
                    continue;

                bool nominalMatch = !string.IsNullOrEmpty(baseNominal)
                    && string.Equals(baseNominal, encNominal, StringComparison.OrdinalIgnoreCase);

                bool dimensionMatch = SharedRules.EnclosureDimensionsMatch(
                    baseLength, baseWidthActual, encDoorWidth, encReturnWidth, tolerance);

                if (nominalMatch || dimensionMatch)
                    matchingEnclosures.Add(MapToCompatibleDto(enc));
            }

            if (matchingEnclosures.Count > 0)
            {
                bool supportsBoth = baseInstall.Contains("alcove") && baseInstall.Contains("corner");
                string categoryName = supportsBoth ? "Corner Enclosures" : "Enclosures";
                results.Add(new CompatibilityCategoryResult { Category = categoryName, Products = SortByRanking(matchingEnclosures) });
            }
        }

        // ---------- Screens ----------
        if (!incompatibilityReasons.ContainsKey("Shower Doors"))
        {
            var matchingScreens = new List<CompatibleProductDto>();

            foreach (var screen in showerScreens)
            {
                var screenAttrs = ProductAttributes.Parse(screen.Attributes);
                var screenPanelWidth = screenAttrs.GetDecimal("Fixed Panel Width");
                var screenSeries = screen.Series;
                var screenBrand = screen.Brand;

                if (SharedRules.IsScreenCompatible(baseWidth, screenPanelWidth)
                    && SharedRules.SeriesCompatible(baseSeries, screenSeries, baseBrand, screenBrand)
                    && (baseInstall.Contains("alcove") || baseInstall.Contains("corner")))
                {
                    matchingScreens.Add(MapToCompatibleDto(screen));
                }
            }

            if (matchingScreens.Count > 0)
                results.Add(new CompatibilityCategoryResult { Category = "Screens", Products = SortByRanking(matchingScreens) });
        }

        // ---------- Walls ----------
        if (!incompatibilityReasons.ContainsKey("Walls"))
        {
            var matchingWalls = FindCompatibleWalls(
                baseProduct, walls, baseInstall, baseSeries, baseBrand, baseFamily,
                baseNominal, baseLength, baseWidthActual,
                CompatibilityConstants.ShowerBaseUtileFamilies,
                wallTypeFilter: new[] { "alcove shower", "corner shower" },
                installCheck: (wallType) =>
                {
                    if (wallType.Contains("alcove shower") && (baseInstall == "alcove" || baseInstall == "alcove or corner"))
                        return true;
                    if (wallType.Contains("corner shower") && (baseInstall == "corner" || baseInstall == "alcove or corner"))
                        return true;
                    return false;
                });

            if (matchingWalls.Count > 0)
                results.Add(new CompatibilityCategoryResult { Category = "Walls", Products = SortByRanking(matchingWalls) });
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
        var order = CompatibilityConstants.ShowerBaseCategoryOrder;
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

    /// <summary>
    /// Find compatible walls using nominal match and cut-to-size closest selection.
    /// Shared between shower base and bathtub rules.
    /// </summary>
    public static List<CompatibleProductDto> FindCompatibleWalls(
        Product baseProduct,
        List<Product> walls,
        string baseInstall,
        string? baseSeries,
        string? baseBrand,
        string? baseFamily,
        string? baseNominal,
        decimal? baseLength,
        decimal? baseWidthActual,
        HashSet<string> utileAllowedFamilies,
        string[] wallTypeFilter,
        Func<string, bool> installCheck)
    {
        var nominalMatches = new List<CompatibleProductDto>();
        var cutCandidates = new List<(Product Wall, string Family, decimal Length, decimal Width)>();

        foreach (var wall in walls)
        {
            var wallAttrs = ProductAttributes.Parse(wall.Attributes);
            var wallType = (wallAttrs.GetString("Type") ?? "").ToLowerInvariant();
            var wallSeries = wall.Series;
            var wallBrand = wall.Brand;
            var wallFamily = wall.Family;
            var wallNominal = wall.NominalDimensions;
            var wallLength = wall.Length;
            var wallWidth = wall.Width;
            var wallCut = wallAttrs.GetString("Cut to Size");

            if (string.IsNullOrEmpty(wall.Sku))
                continue;

            if (!installCheck(wallType))
                continue;

            if (!SharedRules.SeriesCompatible(baseSeries, wallSeries, baseBrand, wallBrand))
                continue;

            if (!SharedRules.BrandFamilyMatch(baseFamily, wallFamily, utileAllowedFamilies))
                continue;

            // Nominal match (only if NOT cut to size)
            if (!string.IsNullOrEmpty(baseNominal)
                && string.Equals(baseNominal, wallNominal, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(wallCut, "Yes", StringComparison.OrdinalIgnoreCase))
            {
                nominalMatches.Add(MapToCompatibleDto(wall));
            }
            // Cut-to-size candidate
            else if (string.Equals(wallCut, "Yes", StringComparison.OrdinalIgnoreCase)
                && baseLength.HasValue && baseWidthActual.HasValue
                && wallLength.HasValue && wallWidth.HasValue
                && wallLength.Value >= baseLength.Value
                && wallWidth.Value >= baseWidthActual.Value)
            {
                var fam = (wallFamily ?? "").Trim().ToLowerInvariant();
                cutCandidates.Add((wall, fam, wallLength.Value, wallWidth.Value));
            }
        }

        // Select closest cut-to-size walls per family
        var closestCutWalls = new List<CompatibleProductDto>();
        if (cutCandidates.Count > 0)
        {
            var byFamily = cutCandidates.GroupBy(c => c.Family);
            foreach (var group in byFamily)
            {
                var minLen = group.Min(c => c.Length);
                var minWidth = group.Where(c => c.Length == minLen).Min(c => c.Width);
                var closest = group.Where(c => c.Length == minLen && c.Width == minWidth);
                closestCutWalls.AddRange(closest.Select(c => MapToCompatibleDto(c.Wall)));
            }
        }

        var result = new List<CompatibleProductDto>();
        result.AddRange(nominalMatches);
        result.AddRange(closestCutWalls);
        return result;
    }

    internal static CompatibleProductDto MapToCompatibleDto(Product product)
    {
        return new CompatibleProductDto
        {
            Sku = product.Sku,
            Name = product.ProductName,
            Brand = product.Brand,
            Series = product.Series,
            Family = product.Family,
            Category = product.Category,
            ImageUrl = product.ImageUrl,
            ProductPageUrl = product.ProductPageUrl,
            CompatibilityScore = product.Ranking ?? 999,
            IsCombo = false
        };
    }

    private static List<CompatibleProductDto> SortByRanking(List<CompatibleProductDto> products)
    {
        return products.OrderBy(p => p.CompatibilityScore ?? 999).ToList();
    }
}

/// <summary>
/// Helper to parse the JSON attributes column from products.
/// Fields like "Max Door Width", "Installation", etc. are stored in this JSON.
/// </summary>
internal class ProductAttributes
{
    private readonly Dictionary<string, JsonElement>? _data;

    private ProductAttributes(Dictionary<string, JsonElement>? data)
    {
        _data = data;
    }

    public static ProductAttributes Parse(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
            return new ProductAttributes(null);

        try
        {
            var doc = JsonDocument.Parse(json);
            var dict = new Dictionary<string, JsonElement>(StringComparer.OrdinalIgnoreCase);
            foreach (var prop in doc.RootElement.EnumerateObject())
            {
                dict[prop.Name] = prop.Value.Clone();
            }
            return new ProductAttributes(dict);
        }
        catch
        {
            return new ProductAttributes(null);
        }
    }

    public string? GetString(string key)
    {
        if (_data == null || !_data.TryGetValue(key, out var element))
            return null;

        return element.ValueKind switch
        {
            JsonValueKind.String => element.GetString(),
            JsonValueKind.Number => element.GetRawText(),
            JsonValueKind.Null => null,
            _ => element.GetRawText()
        };
    }

    public decimal? GetDecimal(string key)
    {
        if (_data == null || !_data.TryGetValue(key, out var element))
            return null;

        return element.ValueKind switch
        {
            JsonValueKind.Number => element.GetDecimal(),
            JsonValueKind.String when decimal.TryParse(element.GetString(), out var v) => v,
            _ => null
        };
    }
}
