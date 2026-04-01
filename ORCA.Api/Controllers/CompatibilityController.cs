using Microsoft.AspNetCore.Mvc;
using ORCA.Api.DTOs;
using ORCA.Api.Services;

namespace ORCA.Api.Controllers;

[ApiController]
public class CompatibilityController : ControllerBase
{
    private readonly ICompatibilityService _compatibilityService;
    private readonly IProductService _productService;

    public CompatibilityController(
        ICompatibilityService compatibilityService,
        IProductService productService)
    {
        _compatibilityService = compatibilityService;
        _productService = productService;
    }

    /// <summary>
    /// GET /api/compatible/{sku}?category=Walls&amp;brand=MAAX&amp;limit=100
    /// Get compatible products for a SKU (matches Python API route).
    /// </summary>
    [HttpGet("api/compatible/{sku}")]
    public async Task<IActionResult> GetCompatible(
        string sku,
        [FromQuery] string? category = null,
        [FromQuery] string? brand = null,
        [FromQuery] int limit = 100)
    {
        var result = await _compatibilityService.GetCompatibleProductsAsync(sku, category, brand, limit);

        if (!result.Success)
            return NotFound(result);

        return Ok(result);
    }

    /// <summary>
    /// POST /api/compute-compatibilities
    /// Trigger a global recompute of all pre-computed compatibility matches.
    /// </summary>
    [HttpPost("api/compute-compatibilities")]
    public async Task<IActionResult> ComputeAll()
    {
        var products = await _productService.GetAllAsync(page: 1, pageSize: int.MaxValue);
        int count = 0;
        int errors = 0;

        foreach (var p in products.Products)
        {
            try
            {
                await _compatibilityService.ComputeCompatibilitiesAsync(p.Sku);
                count++;
            }
            catch
            {
                errors++;
            }
        }

        return Ok(new
        {
            success = true,
            message = $"Recomputed compatibilities for {count} products ({errors} errors)",
            productsProcessed = count,
            errors
        });
    }

    /// <summary>
    /// GET /api/categories
    /// Get all product categories (matches Python API route).
    /// </summary>
    [HttpGet("api/categories")]
    public async Task<IActionResult> GetCategories()
    {
        var categories = await _productService.GetCategoriesAsync();

        return Ok(new
        {
            success = true,
            categories = categories.Select(c => new { category = c.Category, count = c.Count })
        });
    }

    /// <summary>
    /// POST /api/compatibility/search
    /// Search for compatible products with filters.
    /// </summary>
    [HttpPost("api/compatibility/search")]
    public async Task<IActionResult> Search([FromBody] CompatibilitySearchRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Sku))
            return BadRequest(new { success = false, error = "SKU is required" });

        var result = await _compatibilityService.SearchAsync(request);

        if (!result.Success)
            return NotFound(result);

        return Ok(result);
    }

    /// <summary>
    /// POST /api/compatibility/compute/{sku}
    /// Force recomputation of compatibility for a specific product.
    /// </summary>
    [HttpPost("api/compatibility/compute/{sku}")]
    public async Task<IActionResult> Compute(string sku)
    {
        var result = await _compatibilityService.ComputeCompatibilitiesAsync(sku);

        if (!result.Success)
            return NotFound(result);

        return Ok(result);
    }

    /// <summary>
    /// GET /api/compatibility/categories
    /// Get all product categories (original C# route).
    /// </summary>
    [HttpGet("api/compatibility/categories")]
    public async Task<IActionResult> GetCompatibilityCategories()
    {
        var categories = await _productService.GetCategoriesAsync();

        return Ok(new
        {
            success = true,
            categories = categories.Select(c => new { category = c.Category, count = c.Count })
        });
    }
}
