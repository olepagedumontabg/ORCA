using System.Text.Json.Serialization;
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
    /// Returns displaySuggestions in camelCase to match the original Python API and existing JS.
    /// </summary>
    [HttpGet("/suggest")]
    public async Task<IActionResult> Suggest([FromQuery] string? q)
    {
        if (string.IsNullOrWhiteSpace(q) || q.Length < 2)
            return Ok(new SuggestResponse());

        // SKUs are stored uppercase — compare against an uppercased query so PostgreSQL
        // can use the existing B-tree index on sku (LOWER(sku) LIKE '%q%' bypasses it).
        var skuQuery = q.Trim().ToUpperInvariant();
        var nameQuery = q.Trim().ToLowerInvariant();

        // Fetch more raw rows than needed — config SKUs (e.g. 420006-501-001) will be
        // stripped to their base SKU (420006) and deduplicated, so we need extra headroom.
        var rawMatches = await _db.Products
            .AsNoTracking()
            .Where(p =>
                p.Sku.StartsWith(skuQuery) ||
                (p.ProductName != null && p.ProductName.ToLower().Contains(nameQuery)))
            .OrderBy(p => p.Sku.StartsWith(skuQuery) ? 0 : 1)
            .ThenBy(p => p.Sku)
            .Take(100)
            .Select(p => new { p.Sku, p.ProductName, p.Category })
            .ToListAsync();

        // Deduplicate by base SKU (everything before the first '-').
        // Ensures config-only products (no bare base row) still surface as base SKU.
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var matches = new List<(string BaseSku, string? Name, string? Category)>();
        foreach (var m in rawMatches)
        {
            var baseSku = m.Sku.Contains('-') ? m.Sku[..m.Sku.IndexOf('-')] : m.Sku;
            if (seen.Add(baseSku))
            {
                matches.Add((baseSku, m.ProductName, m.Category));
                if (matches.Count == 20) break;
            }
        }

        return Ok(new SuggestResponse
        {
            Suggestions = matches.Select(m => m.BaseSku).ToList(),
            DisplaySuggestions = matches
                .Select(m => string.IsNullOrWhiteSpace(m.Name)
                    ? m.BaseSku
                    : $"{m.BaseSku} - {m.Name}")
                .ToList(),
            Categories = matches.Select(m => m.Category ?? string.Empty).ToList()
        });
    }
}

public class SuggestResponse
{
    [JsonPropertyName("suggestions")]
    public List<string> Suggestions { get; set; } = new();

    [JsonPropertyName("displaySuggestions")]
    public List<string> DisplaySuggestions { get; set; } = new();

    [JsonPropertyName("categories")]
    public List<string> Categories { get; set; } = new();
}
