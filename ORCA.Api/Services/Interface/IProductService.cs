using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;

namespace ORCA.Api.Services.Interface;

public interface IProductService
{
    Task<Product?> GetBySkuAsync(string sku);
    Task<Product?> GetByIdAsync(int id);
    Task<(List<ProductDto> Products, int TotalCount)> GetAllAsync(int page = 1, int pageSize = 50, string? category = null);
    Task<List<(string Category, int Count)>> GetCategoriesAsync();
    Task<List<Product>> GetProductsByCategoriesAsync(IEnumerable<string> categories);

    /// <summary>
    /// Find a product where any AlternateId field matches the given value (case-insensitive).
    /// Used to resolve configuration SKUs to their base product when the config SKU
    /// is stored as an alternate ID on the base product record.
    /// </summary>
    Task<Product?> FindByAlternateIdAsync(string alternateId);

    /// <summary>
    /// Returns all sellable configuration variants for a base SKU.
    /// Finds every product whose SKU starts with {baseSku}-, ordered alphabetically.
    /// </summary>
    Task<List<ProductDto>> GetConfigurationsAsync(string baseSku);
}
