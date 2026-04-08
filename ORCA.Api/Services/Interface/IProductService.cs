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
}
