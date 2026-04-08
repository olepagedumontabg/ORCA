using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Interface;

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

    /// <summary>
    /// Bulk recompute compatibilities for a set of SKUs in a single pass.
    /// Loads all products and overrides once, then computes and stores in batch.
    /// Returns the number of SKUs processed.
    /// </summary>
    Task<int> BulkComputeCompatibilitiesAsync(IEnumerable<string> skus);
}
