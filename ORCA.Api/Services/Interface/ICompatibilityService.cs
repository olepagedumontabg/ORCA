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
    /// Only base-type products (Shower Bases, Bathtubs, Showers, Tub-Showers) are computed.
    /// All other products find their compatible bases by querying the stored pairs in reverse.
    /// Returns the number of SKUs processed.
    /// onProgress is called every 50 products with the current done count.
    /// </summary>
    Task<int> BulkComputeCompatibilitiesAsync(IEnumerable<string> skus, Func<int, Task>? onProgress = null);

    /// <summary>
    /// Truncates the entire product_compatibility table. Used before a full recompute
    /// to ensure stale records from any previous architecture are removed cleanly.
    /// </summary>
    Task ClearAllCompatibilitiesAsync();
}
