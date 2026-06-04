using Microsoft.AspNetCore.Mvc;
using ORCA.Api.DTOs;
using ORCA.Api.Services.Interface;

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
    /// GET /api/compatible/{sku}?category=Walls&amp;brand=MAAX
    /// Get compatible products for a SKU (matches Python API route).
    /// </summary>
    [HttpGet("api/compatible/{sku}")]
    public async Task<IActionResult> GetCompatible(
        string sku,
        [FromQuery] string? category = null,
        [FromQuery] string? brand = null,
        [FromQuery] string? serie = null)
    {
        var result = await _compatibilityService.GetCompatibleProductsAsync(sku, category, brand, serie);

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
        // Wipe the table first so stale records from any previous run are gone.
        // This is safe because the full recompute regenerates everything from scratch.
        await _compatibilityService.ClearAllCompatibilitiesAsync();

        int count = 0;
        int errors = 0;

        // Only base-type products are computed. Doors, screens, walls, enclosures,
        // and return panels automatically get reverse results from the stored pairs.
        var baseCategories = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Shower Bases", "Bathtubs", "Showers", "Tub-Showers"
        };

        const int pageSize = 500;
        int page = 1;

        while (true)
        {
            var result = await _productService.GetAllAsync(page, pageSize);

            if (result.Products == null || !result.Products.Any())
                break;

            foreach (var p in result.Products)
            {
                if (!baseCategories.Contains(p.Category ?? ""))
                    continue;

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

            page++;
        }

        return Ok(new
        {
            success = true,
            message = $"Recomputed compatibilities for {count} base products ({errors} errors)",
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
