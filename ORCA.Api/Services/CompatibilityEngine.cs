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

            _ => new List<CompatibilityCategoryResult>()
        };
    }

    // NOTE: Reverse lookups (door → base, screen → base, etc.) are NOT computed here.
    // They are derived at query time by reading the pre-computed table from the other
    // direction: WHERE compatible_product_id = <this product's id>.
    // This ensures there is exactly one source of truth for every compatible pair.
}
