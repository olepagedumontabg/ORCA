using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Services;

public class SearchService : ISearchService
{
    private readonly OrcaDbContext _db;

    public SearchService(OrcaDbContext db)
    {
        _db = db;
    }

    public async Task<SearchSuggestResult> SuggestAsync(string query, bool exactSkus = false)
    {
        if (string.IsNullOrWhiteSpace(query) || query.Length < 2)
            return new SearchSuggestResult([], [], []);

        var skuQuery  = query.Trim().ToUpperInvariant();
        var nameQuery = query.Trim().ToLowerInvariant();

        if (exactSkus)
        {
            // Return the actual stored SKUs — no base-SKU stripping.
            // Used by the overrides page so the selected value always matches
            // a real product row and passes exact-match validation.
            var exact = await _db.Products
                .AsNoTracking()
                .Where(p => p.Sku.StartsWith(skuQuery))
                .OrderBy(p => p.Sku)
                .Take(20)
                .Select(p => new { p.Sku, p.ProductName, p.Category })
                .ToListAsync();

            return new SearchSuggestResult(
                Suggestions:        exact.Select(m => m.Sku).ToList(),
                DisplaySuggestions: exact.Select(m =>
                    string.IsNullOrWhiteSpace(m.ProductName) ? m.Sku : $"{m.Sku} - {m.ProductName}").ToList(),
                Categories: exact.Select(m => m.Category ?? string.Empty).ToList()
            );
        }

        // Default: fetch more raw rows than needed — config SKUs will be stripped
        // to base SKU and deduplicated, so we need extra headroom.
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
        var seen    = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
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

        return new SearchSuggestResult(
            Suggestions:        matches.Select(m => m.BaseSku).ToList(),
            DisplaySuggestions: matches
                .Select(m => string.IsNullOrWhiteSpace(m.Name)
                    ? m.BaseSku
                    : $"{m.BaseSku} - {m.Name}")
                .ToList(),
            Categories: matches.Select(m => m.Category ?? string.Empty).ToList()
        );
    }
}
