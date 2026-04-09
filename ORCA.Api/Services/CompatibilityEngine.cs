using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;
using ORCA.Api.Services.Interface;
using ORCA.Api.Services.Rules;

namespace ORCA.Api.Services;

/// <summary>
/// Routes compatibility computation to the appropriate rule class based on product category.
/// Migrated from logic/compatibility.py find_compatible_products().
/// </summary>
public class CompatibilityEngine : ICompatibilityEngine
{
    private readonly ILogger<CompatibilityEngine> _logger;

    public CompatibilityEngine(ILogger<CompatibilityEngine> logger)
    {
        _logger = logger;
    }

    public List<CompatibilityCategoryResult> FindCompatibleProducts(
        Product baseProduct,
        Dictionary<string, List<Product>> candidatesByCategory)
    {
        var category = baseProduct.Category;
        _logger.LogDebug("Computing compatibility for {Sku} (category: {Category})", baseProduct.Sku, category);

        List<Product> GetCandidates(string cat) =>
            candidatesByCategory.TryGetValue(cat, out var list) ? list : new List<Product>();

        return category switch
        {
            CompatibilityConstants.Categories.ShowerBases => ShowerBaseRules.FindCompatibilities(
                baseProduct,
                showerDoors: GetCandidates(CompatibilityConstants.Categories.ShowerDoors),
                returnPanels: GetCandidates(CompatibilityConstants.Categories.ReturnPanels),
                enclosures: GetCandidates(CompatibilityConstants.Categories.Enclosures),
                showerScreens: GetCandidates(CompatibilityConstants.Categories.ShowerScreens),
                walls: GetCandidates(CompatibilityConstants.Categories.Walls)),

            CompatibilityConstants.Categories.Bathtubs => BathtubRules.FindCompatibilities(
                baseProduct,
                tubDoors: GetCandidates(CompatibilityConstants.Categories.TubDoors),
                tubScreens: GetCandidates(CompatibilityConstants.Categories.TubScreens),
                walls: GetCandidates(CompatibilityConstants.Categories.Walls)),

            CompatibilityConstants.Categories.Showers => ShowerRules.FindCompatibilities(
                baseProduct,
                showerDoors: GetCandidates(CompatibilityConstants.Categories.ShowerDoors)),

            CompatibilityConstants.Categories.TubShowers => TubShowerRules.FindCompatibilities(
                baseProduct,
                tubDoors: GetCandidates(CompatibilityConstants.Categories.TubDoors)),

            // Reverse compatibility: screens find compatible bases/bathtubs
            CompatibilityConstants.Categories.ShowerScreens => FindReverseScreenCompatibility(
                baseProduct, GetCandidates(CompatibilityConstants.Categories.ShowerBases), "Shower Bases"),

            CompatibilityConstants.Categories.TubScreens => FindReverseScreenCompatibility(
                baseProduct, GetCandidates(CompatibilityConstants.Categories.Bathtubs), "Bathtubs"),

            // Reverse compatibility: enclosures find compatible bases
            CompatibilityConstants.Categories.Enclosures => FindReverseEnclosureCompatibility(
                baseProduct, GetCandidates(CompatibilityConstants.Categories.ShowerBases)),

            // Reverse compatibility: doors find compatible bases/bathtubs
            CompatibilityConstants.Categories.ShowerDoors => FindReverseDoorCompatibility(
                baseProduct, GetCandidates(CompatibilityConstants.Categories.ShowerBases), "Shower Bases", isShowerDoor: true),

            CompatibilityConstants.Categories.TubDoors => FindReverseDoorCompatibility(
                baseProduct, GetCandidates(CompatibilityConstants.Categories.Bathtubs), "Bathtubs", isShowerDoor: false),

            _ =>
            [
                new CompatibilityCategoryResult
                {
                    Category = category,
                    IncompatibilityReason = $"No compatibility rules defined for category '{category}'"
                }
            ]
        };
    }

    private List<CompatibilityCategoryResult> FindReverseScreenCompatibility(
        Product screen, List<Product> fixtures, string resultCategory)
    {
        var screenAttrs = ProductAttributes.Parse(screen.Attributes);
        var screenPanelWidth = screenAttrs.GetDecimal("Fixed Panel Width");
        var screenSeries = screen.Series;
        var screenBrand = screen.Brand;

        var matches = new List<CompatibleProductDto>();

        foreach (var fixture in fixtures)
        {
            var fixtureAttrs = ProductAttributes.Parse(fixture.Attributes);
            var fixtureWidth = fixtureAttrs.GetDecimal("Max Door Width");

            if (SharedRules.IsScreenCompatible(fixtureWidth, screenPanelWidth)
                && SharedRules.SeriesCompatible(fixture.Series, screenSeries))
            {
                matches.Add(ShowerBaseRules.MapToCompatibleDto(fixture));
            }
        }

        var results = new List<CompatibilityCategoryResult>();
        if (matches.Count > 0)
        {
            results.Add(new CompatibilityCategoryResult
            {
                Category = resultCategory,
                Products = matches
            });
        }
        return results;
    }

    private List<CompatibilityCategoryResult> FindReverseEnclosureCompatibility(
        Product enclosure, List<Product> showerBases)
    {
        var encAttrs = ProductAttributes.Parse(enclosure.Attributes);
        var encNominal = enclosure.NominalDimensions;
        var encDoorWidth = encAttrs.GetDecimal("Door Width");
        var encReturnWidth = encAttrs.GetDecimal("Return Panel Width");
        var encSeries = enclosure.Series;
        var encBrand = enclosure.Brand;

        var matches = new List<CompatibleProductDto>();
        const decimal tolerance = CompatibilityConstants.EnclosureToleranceReverse;

        foreach (var baseProduct in showerBases)
        {
            var baseInstall = (ProductAttributes.Parse(baseProduct.Attributes)
                .GetString("Installation") ?? "").ToLowerInvariant();

            if (!baseInstall.Contains("corner"))
                continue;

            if (!SharedRules.SeriesCompatible(encSeries, baseProduct.Series, encBrand, baseProduct.Brand))
                continue;

            bool nominalMatch = !string.IsNullOrEmpty(encNominal)
                && string.Equals(baseProduct.NominalDimensions, encNominal, StringComparison.OrdinalIgnoreCase);

            bool dimensionMatch = SharedRules.EnclosureDimensionsMatch(
                baseProduct.Length, baseProduct.Width, encDoorWidth, encReturnWidth, tolerance);

            if (nominalMatch || dimensionMatch)
                matches.Add(ShowerBaseRules.MapToCompatibleDto(baseProduct));
        }

        var results = new List<CompatibilityCategoryResult>();
        if (matches.Count > 0)
        {
            results.Add(new CompatibilityCategoryResult
            {
                Category = "Shower Bases",
                Products = matches
            });
        }
        return results;
    }

    private List<CompatibilityCategoryResult> FindReverseDoorCompatibility(
        Product door, List<Product> fixtures, string resultCategory, bool isShowerDoor)
    {
        var doorAttrs = ProductAttributes.Parse(door.Attributes);
        var doorMinWidth = doorAttrs.GetDecimal("Minimum Width");
        var doorMaxWidth = doorAttrs.GetDecimal("Maximum Width");
        var doorSeries = door.Series;
        var doorBrand = door.Brand;

        var matches = new List<CompatibleProductDto>();

        foreach (var fixture in fixtures)
        {
            var fixtureAttrs = ProductAttributes.Parse(fixture.Attributes);
            var fixtureWidth = fixtureAttrs.GetDecimal("Max Door Width");
            var fixtureInstall = (fixtureAttrs.GetString("Installation") ?? "").ToLowerInvariant();

            // For shower doors: base must support alcove or corner
            // For tub doors: base must be Alcove
            bool installOk = isShowerDoor
                ? (fixtureInstall.Contains("alcove") || fixtureInstall.Contains("corner"))
                : string.Equals(fixtureInstall, "alcove", StringComparison.OrdinalIgnoreCase);

            if (installOk
                && SharedRules.DoorWidthFits(doorMinWidth, doorMaxWidth, fixtureWidth)
                && SharedRules.SeriesCompatible(fixture.Series, doorSeries, fixture.Brand, doorBrand))
            {
                matches.Add(ShowerBaseRules.MapToCompatibleDto(fixture));
            }
        }

        var results = new List<CompatibilityCategoryResult>();
        if (matches.Count > 0)
        {
            results.Add(new CompatibilityCategoryResult
            {
                Category = resultCategory,
                Products = matches
            });
        }
        return results;
    }
}
