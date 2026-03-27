using Microsoft.AspNetCore.Mvc;
using ORCA.Api.DTOs;
using ORCA.Api.Services;

namespace ORCA.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
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
    /// POST /api/compatibility/search
    /// Search for compatible products with filters.
    /// </summary>
    [HttpPost("search")]
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
    /// Force recomputation of compatibility for a product.
    /// </summary>
    [HttpPost("compute/{sku}")]
    public async Task<IActionResult> Compute(string sku)
    {
        var result = await _compatibilityService.ComputeCompatibilitiesAsync(sku);

        if (!result.Success)
            return NotFound(result);

        return Ok(result);
    }

    /// <summary>
    /// GET /api/compatibility/categories
    /// Get all product categories with counts.
    /// </summary>
    [HttpGet("categories")]
    public async Task<IActionResult> GetCategories()
    {
        var categories = await _productService.GetCategoriesAsync();

        return Ok(new
        {
            success = true,
            categories = categories.Select(c => new { category = c.Category, count = c.Count })
        });
    }
}
