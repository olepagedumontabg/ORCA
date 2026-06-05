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
    /// Returns all sellable configuration variants for a parent product.
    /// Finds every product whose ParentId matches the given value (case-insensitive),
    /// ordered alphabetically by SKU.
    /// </summary>
    Task<List<ProductDto>> GetConfigurationsAsync(string parentId);

    /// <summary>
    /// Returns the first child product (ordered by SKU) whose ParentId matches the
    /// given value. Used to resolve a parent SKU to a representative child when the
    /// parent itself has no standalone product row.
    /// </summary>
    Task<Product?> FindFirstChildByParentIdAsync(string parentId);
}
