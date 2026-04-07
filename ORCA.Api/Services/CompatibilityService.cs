using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Services;

public class CompatibilityService : ICompatibilityService
{
    private readonly OrcaDbContext _db;
    private readonly IProductService _productService;
    private readonly ICompatibilityEngine _engine;
    private readonly ILogger<CompatibilityService> _logger;

    public CompatibilityService(
        OrcaDbContext db,
        IProductService productService,
        ICompatibilityEngine engine,
        ILogger<CompatibilityService> logger)
    {
        _db = db;
        _productService = productService;
        _engine = engine;
        _logger = logger;
    }

    public async Task<CompatibilityResultDto> GetCompatibleProductsAsync(string sku, string? categoryFilter = null, string? brandFilter = null, string? serieFilter = null)
    {
        sku = sku.Trim().ToUpper();

        var product = await _productService.GetBySkuAsync(sku);

        if (product == null)
        {
            return new CompatibilityResultDto
            {
                Success = false,
                ErrorMessage = $"Product not found: {sku}"
            };
        }

        // Try pre-computed results first
        var precomputed = await LoadPrecomputedCompatibilitiesAsync(product.Id);

        // Cascade through alternate IDs if no pre-computed data found
        foreach (var altSku in new[] { product.AlternateId1, product.AlternateId2, product.AlternateId3 })
        {
            if (precomputed != null && precomputed.Count > 0) break;
            if (string.IsNullOrEmpty(altSku)) continue;
            var altProduct = await _productService.GetBySkuAsync(altSku);
            if (altProduct != null)
                precomputed = await LoadPrecomputedCompatibilitiesAsync(altProduct.Id);
        }

        List<CompatibilityCategoryResult> categories;

        if (precomputed != null && precomputed.Count > 0)
        {
            categories = precomputed;
            _logger.LogInformation("Using pre-computed compatibilities for {Sku} ({Count} categories)",
                sku, categories.Count);
        }
        else
        {
            // On-demand computation
            categories = await ComputeOnDemandAsync(product);
            _logger.LogInformation("Computed on-demand compatibilities for {Sku} ({Count} categories)",
                sku, categories.Count);
        }

        // Apply filters
        categories = ApplyFilters(categories, categoryFilter, brandFilter, serieFilter);

        // Build incompatibility reasons dictionary
        var incompatibilityReasons = new Dictionary<string, string>();
        foreach (var cat in categories.Where(c => !string.IsNullOrEmpty(c.IncompatibilityReason)))
        {
            incompatibilityReasons[cat.Category] = cat.IncompatibilityReason!;
        }

        return new CompatibilityResultDto
        {
            Success = true,
            Product = MapToProductDto(product),
            Compatibles = categories.Where(c => c.Products.Count > 0).ToList(),
            IncompatibilityReasons = incompatibilityReasons,
            TotalCategories = categories.Count(c => c.Products.Count > 0),
            DataSource = (precomputed != null && precomputed.Any())
                ? "database"
                : "computed"
        };
    }

    public async Task<CompatibilityResultDto> SearchAsync(CompatibilitySearchRequest request)
    {
        return await GetCompatibleProductsAsync(
            request.Sku, request.Category, request.Brand, request.Serie);
    }

    public async Task<CompatibilityResultDto> ComputeCompatibilitiesAsync(string sku)
    {
        sku = sku.Trim().ToUpper();
        var product = await _productService.GetBySkuAsync(sku);

        if (product == null)
        {
            return new CompatibilityResultDto
            {
                Success = false,
                ErrorMessage = $"Product not found: {sku}"
            };
        }

        var categories = await ComputeOnDemandAsync(product);

        // Store results in product_compatibility table
        await StoreComputedCompatibilitiesAsync(product, categories);

        var incompatibilityReasons = new Dictionary<string, string>();
        foreach (var cat in categories.Where(c => !string.IsNullOrEmpty(c.IncompatibilityReason)))
            incompatibilityReasons[cat.Category] = cat.IncompatibilityReason!;

        return new CompatibilityResultDto
        {
            Success = true,
            Product = MapToProductDto(product),
            Compatibles = categories.Where(c => c.Products.Count > 0).ToList(),
            IncompatibilityReasons = incompatibilityReasons,
            TotalCategories = categories.Count(c => c.Products.Count > 0),
            DataSource = "computed"
        };
    }

    private async Task<List<CompatibilityCategoryResult>?> LoadPrecomputedCompatibilitiesAsync(int baseProductId)
    {
        var rows = await _db.ProductCompatibilities
            .AsNoTracking()
            .Where(pc => pc.BaseProductId == baseProductId
                && (pc.IncompatibilityReason == null || pc.IncompatibilityReason == ""))
            .Include(pc => pc.CompatibleProduct)
            .OrderByDescending(pc => pc.CompatibilityScore)
            .ToListAsync();

        if (rows.Count == 0)
            return null;

        // Check overrides
        var baseSku = await _db.Products.Where(p => p.Id == baseProductId)
            .Select(p => p.Sku).FirstAsync();
        var overrides = await LoadOverridesAsync(baseSku);

        var byCategory = new Dictionary<string, List<CompatibleProductDto>>();

        foreach (var row in rows)
        {
            var compatSku = row.CompatibleProduct.Sku;

            // Apply blacklist
            if (overrides.Blacklisted.Contains(compatSku))
                continue;

            var category = row.CompatibleProduct.Category;
            if (!byCategory.ContainsKey(category))
                byCategory[category] = new List<CompatibleProductDto>();

            byCategory[category].Add(new CompatibleProductDto
            {
                Sku = compatSku,
                Name = row.CompatibleProduct.ProductName,
                Brand = row.CompatibleProduct.Brand,
                Series = row.CompatibleProduct.Series,
                Family = row.CompatibleProduct.Family,
                Category = category,
                ImageUrl = row.CompatibleProduct.ImageUrl,
                ProductPageUrl = row.CompatibleProduct.ProductPageUrl,
                CompatibilityScore = row.CompatibilityScore,
                MatchReason = row.MatchReason
            });
        }

        // Add whitelisted products that aren't already in results
        foreach (var whitelistedSku in overrides.Whitelisted)
        {
            bool alreadyIncluded = byCategory.Values.Any(list => list.Any(p => p.Sku == whitelistedSku));
            if (alreadyIncluded) continue;

            var whitelistedProduct = await _db.Products.AsNoTracking()
                .FirstOrDefaultAsync(p => p.Sku == whitelistedSku);
            if (whitelistedProduct == null) continue;

            var cat = whitelistedProduct.Category;
            if (!byCategory.ContainsKey(cat))
                byCategory[cat] = new List<CompatibleProductDto>();

            byCategory[cat].Add(new CompatibleProductDto
            {
                Sku = whitelistedProduct.Sku,
                Name = whitelistedProduct.ProductName,
                Brand = whitelistedProduct.Brand,
                Series = whitelistedProduct.Series,
                Family = whitelistedProduct.Family,
                Category = cat,
                ImageUrl = whitelistedProduct.ImageUrl,
                ProductPageUrl = whitelistedProduct.ProductPageUrl,
                CompatibilityScore = 1000, // Whitelisted = highest score
                MatchReason = "Whitelisted"
            });
        }

        return byCategory.Select(kvp => new CompatibilityCategoryResult
        {
            Category = kvp.Key,
            Products = kvp.Value
        }).ToList();
    }

    private async Task<List<CompatibilityCategoryResult>> ComputeOnDemandAsync(Product product)
    {
        // Determine which candidate categories are needed
        var candidateCategories = GetCandidateCategories(product.Category);

        // Load all candidate products
        var candidates = await _productService.GetProductsByCategoriesAsync(candidateCategories);

        // Group by category
        var candidatesByCategory = candidates
            .GroupBy(p => p.Category)
            .ToDictionary(g => g.Key, g => g.ToList());

        // Run the compatibility engine
        var results = _engine.FindCompatibleProducts(product, candidatesByCategory);

        // Apply overrides
        var overrides = await LoadOverridesAsync(product.Sku);
        results = ApplyOverrides(results, overrides);

        return results;
    }

    private async Task StoreComputedCompatibilitiesAsync(Product baseProduct, List<CompatibilityCategoryResult> categories)
    {
        // Remove existing
        var existing = await _db.ProductCompatibilities
            .Where(pc => pc.BaseProductId == baseProduct.Id)
            .ToListAsync();

        _db.ProductCompatibilities.RemoveRange(existing);

        // 🔥 Load all products ONCE
        var skus = categories
            .SelectMany(c => c.Products)
            .Select(p => p.Sku)
            .Distinct()
            .ToList();

        var productsMap = await _db.Products
            .Where(p => skus.Contains(p.Sku))
            .ToDictionaryAsync(p => p.Sku, p => p);

        int score = 1000;

        foreach (var category in categories)
        {
            foreach (var compatible in category.Products)
            {
                if (!productsMap.TryGetValue(compatible.Sku, out var compatProduct))
                    continue;

                _db.ProductCompatibilities.Add(new ProductCompatibility
                {
                    BaseProductId = baseProduct.Id,
                    CompatibleProductId = compatProduct.Id,
                    CompatibilityScore = score--,
                    MatchReason = compatible.MatchReason ?? category.Category,
                    ComputedAt = DateTime.UtcNow
                });
            }

            // incompatibility
            if (!string.IsNullOrEmpty(category.IncompatibilityReason))
            {
                _db.ProductCompatibilities.Add(new ProductCompatibility
                {
                    BaseProductId = baseProduct.Id,
                    CompatibleProductId = baseProduct.Id,
                    IncompatibilityReason = category.IncompatibilityReason,
                    ComputedAt = DateTime.UtcNow
                });
            }
        }

        await _db.SaveChangesAsync();
    }

    private static string[] GetCandidateCategories(string productCategory)
    {
        return productCategory switch
        {
            CompatibilityConstants.Categories.ShowerBases => new[]
            {
                CompatibilityConstants.Categories.ShowerDoors,
                CompatibilityConstants.Categories.ReturnPanels,
                CompatibilityConstants.Categories.Enclosures,
                CompatibilityConstants.Categories.ShowerScreens,
                CompatibilityConstants.Categories.Walls
            },
            CompatibilityConstants.Categories.Bathtubs => new[]
            {
                CompatibilityConstants.Categories.TubDoors,
                CompatibilityConstants.Categories.TubScreens,
                CompatibilityConstants.Categories.Walls
            },
            CompatibilityConstants.Categories.Showers => new[]
            {
                CompatibilityConstants.Categories.ShowerDoors
            },
            CompatibilityConstants.Categories.TubShowers => new[]
            {
                CompatibilityConstants.Categories.TubDoors
            },
            CompatibilityConstants.Categories.ShowerScreens => new[]
            {
                CompatibilityConstants.Categories.ShowerBases
            },
            CompatibilityConstants.Categories.TubScreens => new[]
            {
                CompatibilityConstants.Categories.Bathtubs
            },
            CompatibilityConstants.Categories.Enclosures => new[]
            {
                CompatibilityConstants.Categories.ShowerBases
            },
            CompatibilityConstants.Categories.ShowerDoors => new[]
            {
                CompatibilityConstants.Categories.ShowerBases
            },
            CompatibilityConstants.Categories.TubDoors => new[]
            {
                CompatibilityConstants.Categories.Bathtubs
            },
            _ => Array.Empty<string>()
        };
    }

    private async Task<OverrideSet> LoadOverridesAsync(string baseSku)
    {
        var overrides = await _db.CompatibilityOverrides
            .AsNoTracking()
            .Where(o => o.BaseSku == baseSku || o.CompatibleSku == baseSku)
            .ToListAsync();

        var whitelisted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var blacklisted = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var o in overrides)
        {
            var otherSku = string.Equals(o.BaseSku, baseSku, StringComparison.OrdinalIgnoreCase)
                ? o.CompatibleSku : o.BaseSku;

            if (string.Equals(o.OverrideType, "whitelist", StringComparison.OrdinalIgnoreCase))
                whitelisted.Add(otherSku);
            else if (string.Equals(o.OverrideType, "blacklist", StringComparison.OrdinalIgnoreCase))
                blacklisted.Add(otherSku);
        }

        return new OverrideSet(whitelisted, blacklisted);
    }

    private static List<CompatibilityCategoryResult> ApplyOverrides(
        List<CompatibilityCategoryResult> results, OverrideSet overrides)
    {
        foreach (var category in results)
        {
            category.Products = category.Products
                .Where(p => !overrides.Blacklisted.Contains(p.Sku))
                .ToList();
        }
        return results;
    }

    private static List<CompatibilityCategoryResult> ApplyFilters(
        List<CompatibilityCategoryResult> categories,
        string? categoryFilter, string? brandFilter, string? serieFilter)
    {
        if (!string.IsNullOrWhiteSpace(categoryFilter))
        {
            categories = categories
                .Where(c => c.Category.Contains(categoryFilter, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }

        if (!string.IsNullOrWhiteSpace(brandFilter))
        {
            foreach (var cat in categories)
            {
                cat.Products = cat.Products
                    .Where(p => string.Equals(p.Brand, brandFilter, StringComparison.OrdinalIgnoreCase))
                    .ToList();
            }
        }

        if (!string.IsNullOrWhiteSpace(serieFilter))
        {
            foreach (var cat in categories)
            {
                cat.Products = cat.Products
                    .Where(p => string.Equals(p.Series, serieFilter, StringComparison.OrdinalIgnoreCase))
                    .ToList();
            }
        }

        foreach (var cat in categories)
        {
            cat.Products = cat.Products.ToList();
        }

        return categories;
    }

    private static ProductDto MapToProductDto(Product product)
    {
        return new ProductDto
        {
            Id = product.Id,
            Sku = product.Sku,
            Name = product.ProductName,
            Brand = product.Brand,
            Series = product.Series,
            Family = product.Family,
            Category = product.Category,
            ImageUrl = product.ImageUrl,
            ProductPageUrl = product.ProductPageUrl,
            NominalDimensions = product.NominalDimensions,
            AlternateId1 = product.AlternateId1,
            AlternateId2 = product.AlternateId2,
            AlternateId3 = product.AlternateId3
        };
    }

    private record OverrideSet(HashSet<string> Whitelisted, HashSet<string> Blacklisted);
}
