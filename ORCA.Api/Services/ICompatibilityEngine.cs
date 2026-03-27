using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services;

public interface ICompatibilityEngine
{
    /// <summary>
    /// Compute compatible products for a given product using business rules.
    /// This runs the rule engine against candidate products (on-demand computation).
    /// </summary>
    List<CompatibilityCategoryResult> FindCompatibleProducts(
        Product baseProduct,
        Dictionary<string, List<Product>> candidatesByCategory);
}
