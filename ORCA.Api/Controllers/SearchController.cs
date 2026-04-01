using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;

namespace ORCA.Api.Controllers;

[ApiController]
public class SearchController : ControllerBase
{
    private readonly OrcaDbContext _db;

    public SearchController(OrcaDbContext db)
    {
        _db = db;
    }

    /// <summary>
    /// GET /suggest?q=... — SKU / product name autocomplete (matches Python /suggest endpoint)
    /// </summary>
    [HttpGet("/suggest")]
    public async Task<IActionResult> Suggest([FromQuery] string? q)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Length < 2)
            return Ok(new { suggestions = Array.Empty<string>(), displaySuggestions = Array.Empty<string>() });

        var query = q.Trim().ToLower();

        var matches = await _db.Products
            .AsNoTracking()
            .Where(p =>
                p.Sku.ToLower().Contains(query) ||
                (p.ProductName != null && p.ProductName.ToLower().Contains(query)))
            .OrderBy(p => p.Sku.ToLower().StartsWith(query) ? 0 : 1)
            .ThenBy(p => p.Sku)
            .Take(20)
            .Select(p => new { p.Sku, p.ProductName })
            .ToListAsync();

        var suggestions = matches.Select(m => m.Sku).ToList();
        var displaySuggestions = matches
            .Select(m => string.IsNullOrWhiteSpace(m.ProductName) ? m.Sku : $"{m.Sku} - {m.ProductName}")
            .ToList();

        return Ok(new { suggestions, displaySuggestions });
    }
}
