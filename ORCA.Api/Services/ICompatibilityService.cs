using ORCA.Api.DTOs;

namespace ORCA.Api.Services;

public interface ICompatibilityService
{
    /// <summary>
    /// Get compatible products for a SKU. Uses pre-computed results first,
    /// falls back to on-demand computation via the compatibility engine.
    /// </summary>
    Task<CompatibilityResultDto> GetCompatibleProductsAsync(
        string sku, string? categoryFilter = null, string? brandFilter = null, string? serieFilter = null);

    /// <summary>
    /// Search for compatible products using a structured request.
    /// </summary>
    Task<CompatibilityResultDto> SearchAsync(CompatibilitySearchRequest request);

    /// <summary>
    /// Force recomputation of compatibility for a given SKU.
    /// </summary>
    Task<CompatibilityResultDto> ComputeCompatibilitiesAsync(string sku);
}
