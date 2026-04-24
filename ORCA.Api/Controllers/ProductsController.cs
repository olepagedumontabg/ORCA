using Microsoft.AspNetCore.Mvc;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Controllers;

[ApiController]
public class ProductsController : ControllerBase
{
    private readonly IProductService _productService;
    private readonly ICompatibilityService _compatibilityService;

    public ProductsController(IProductService productService, ICompatibilityService compatibilityService)
    {
        _productService = productService;
        _compatibilityService = compatibilityService;
    }

    /// <summary>
    /// GET /api/products?page=1&amp;pageSize=50&amp;category=Shower+Bases
    /// </summary>
    [HttpGet("api/products")]
    public async Task<IActionResult> GetAll(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50,
        [FromQuery] string? category = null)
    {
        var (products, totalCount) = await _productService.GetAllAsync(page, pageSize, category);

        return Ok(new
        {
            success = true,
            products,
            total = totalCount,
            page,
            pageSize
        });
    }

    /// <summary>
    /// GET /api/products/{id}
    /// </summary>
    [HttpGet("api/products/{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var product = await _productService.GetByIdAsync(id);
        if (product == null)
            return NotFound(new { success = false, error = $"Product not found: {id}" });

        return Ok(new { success = true, product = MapProduct(product) });
    }

    /// <summary>
    /// GET /api/product/{sku} — matches Python API route
    /// GET /api/products/sku/{sku} — original C# route
    /// </summary>
    [HttpGet("api/product/{sku}")]
    [HttpGet("api/products/sku/{sku}")]
    public async Task<IActionResult> GetBySku(string sku)
    {
        var product = await _productService.GetBySkuAsync(sku);
        if (product == null)
            return NotFound(new { success = false, error = $"Product not found: {sku}" });

        return Ok(new { success = true, product = MapProduct(product) });
    }

    /// <summary>
    /// GET /api/products/{id}/compatible?category=Walls&amp;brand=MAAX&amp;limit=50
    /// </summary>
    [HttpGet("api/products/{id:int}/compatible")]
    public async Task<IActionResult> GetCompatibleById(
        int id,
        [FromQuery] string? category = null,
        [FromQuery] string? brand = null,
        [FromQuery] string? serie = null)
    {
        var product = await _productService.GetByIdAsync(id);
        if (product == null)
            return NotFound(new { success = false, error = $"Product not found: {id}" });

        var result = await _compatibilityService.GetCompatibleProductsAsync(
            product.Sku, category, brand, serie);

        return Ok(result);
    }

    /// <summary>
    /// GET /api/products/sku/{sku}/compatible?category=Walls&amp;brand=MAAX&amp;limit=50
    /// </summary>
    [HttpGet("api/products/sku/{sku}/compatible")]
    public async Task<IActionResult> GetCompatibleBySku(
        string sku,
        [FromQuery] string? category = null,
        [FromQuery] string? brand = null,
        [FromQuery] string? serie = null)
    {
        var result = await _compatibilityService.GetCompatibleProductsAsync(
            sku, category, brand, serie);

        if (!result.Success)
            return NotFound(result);

        return Ok(result);
    }

    /// <summary>
    /// GET /api/product/{sku}/configurations
    /// Returns all sellable configuration variants for a base SKU.
    /// Pass the base SKU (e.g. 148006) or any config SKU (e.g. 148006-L-000-002) —
    /// both resolve to the same base and return the same list.
    /// Returns an empty array when the product has no split configurations
    /// (all variants share the same dimensions and are managed at the base level).
    /// </summary>
    [HttpGet("api/product/{sku}/configurations")]
    public async Task<IActionResult> GetConfigurations(string sku)
    {
        var baseSku = sku.Trim().ToUpperInvariant();
        if (baseSku.Contains('-'))
            baseSku = baseSku[..baseSku.IndexOf('-')];

        var configurations = await _productService.GetConfigurationsAsync(baseSku);

        return Ok(new
        {
            success = true,
            baseSku,
            hasConfigurations = configurations.Count > 0,
            configurations
        });
    }

    private static object MapProduct(ORCA.Api.Domain.Entities.Product product) => new
    {
        product.Id,
        product.Sku,
        name = product.ProductName,
        product.Brand,
        product.Series,
        product.Family,
        product.Category,
        product.ImageUrl,
        product.ProductPageUrl,
        product.NominalDimensions,
        product.Length,
        product.Width,
        product.Height,
        product.Ranking
    };
}
