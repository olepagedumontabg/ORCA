using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Services;

public class ProductService : IProductService
{
    private readonly OrcaDbContext _db;

    public ProductService(OrcaDbContext db)
    {
        _db = db;
    }

    public async Task<Product?> GetBySkuAsync(string sku)
    {
        return await _db.Products
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Sku == sku.ToUpper());
    }

    public async Task<Product?> GetByIdAsync(int id)
    {
        return await _db.Products
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == id);
    }

    public async Task<(List<ProductDto> Products, int TotalCount)> GetAllAsync(
        int page = 1, int pageSize = 50, string? category = null)
    {
        var query = _db.Products.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(category))
            query = query.Where(p => p.Category == category);

        var totalCount = await query.CountAsync();

        var products = await query
            .OrderBy(p => p.Sku)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(p => new ProductDto
            {
                Id = p.Id,
                Sku = p.Sku,
                Name = p.ProductName,
                Brand = p.Brand,
                Series = p.Series,
                Family = p.Family,
                Category = p.Category,
                ImageUrl = p.ImageUrl,
                ProductPageUrl = p.ProductPageUrl,
                NominalDimensions = p.NominalDimensions,
                AlternateId1 = p.AlternateId1,
                AlternateId2 = p.AlternateId2,
                AlternateId3 = p.AlternateId3
            })
            .ToListAsync();

        return (products, totalCount);
    }

    public async Task<List<(string Category, int Count)>> GetCategoriesAsync()
    {
        var rows = await _db.Products
            .AsNoTracking()
            .GroupBy(p => p.Category)
            .Select(g => new { Category = g.Key, Count = g.Count() })
            .OrderBy(x => x.Category)
            .ToListAsync();

        return rows.Select(x => (x.Category, x.Count)).ToList();
    }

    public async Task<List<Product>> GetProductsByCategoriesAsync(IEnumerable<string> categories)
    {
        return await _db.Products
            .AsNoTracking()
            .Where(p => categories.Contains(p.Category))
            .ToListAsync();
    }
}
