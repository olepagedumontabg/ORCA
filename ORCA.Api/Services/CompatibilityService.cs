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

        // Not found by exact SKU — try a reverse AlternateId lookup.
        // Some products are browsed by their sellable/configuration SKU on the website
        // (e.g. "410006-501-001"), which may be stored as an AlternateId on the base
        // product record ("410006") rather than as its own row in the DB.
        if (product == null)
        {
            product = await _productService.FindByAlternateIdAsync(sku);
            if (product != null)
                _logger.LogInformation("Resolved {ConfigSku} → base product {BaseSku} via alternate ID", sku, product.Sku);
        }

        // Still not found — try stripping the configuration suffix progressively.
        // e.g. "410006-501-001" → "410006-501" → "410006"
        if (product == null)
        {
            product = await TryFindByStrippedSkuAsync(sku);
            if (product != null)
                _logger.LogInformation("Resolved {ConfigSku} → base product {BaseSku} via suffix stripping", sku, product.Sku);
        }

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

            // Persist the computed results (+ their reverse records) so that related products
            // (e.g. walls, doors) can find this product in subsequent look-ups without needing
            // their own rules in the engine.
            if (categories.Count > 0)
                await StoreComputedCompatibilitiesAsync(product, categories);
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

    public async Task<int> BulkComputeCompatibilitiesAsync(IEnumerable<string> skus, Func<int, Task>? onProgress = null)
    {
        var skuSet = skus
            .Select(s => s.Trim().ToUpperInvariant())
            .Where(s => !string.IsNullOrEmpty(s))
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        if (skuSet.Count == 0) return 0;

        // Load ALL products once, grouped by category
        var allProducts = await _db.Products.AsNoTracking().ToListAsync();
        var byCategory = allProducts
            .GroupBy(p => p.Category)
            .ToDictionary(g => g.Key, g => g.ToList());
        var bySku = allProducts.ToDictionary(p => p.Sku, p => p, StringComparer.OrdinalIgnoreCase);

        // Load ALL overrides once
        var allOverrides = await _db.CompatibilityOverrides.AsNoTracking().ToListAsync();
        var overridesBySku = new Dictionary<string, OverrideSet>(StringComparer.OrdinalIgnoreCase);
        foreach (var o in allOverrides)
        {
            foreach (var thisSku in new[] { o.BaseSku, o.CompatibleSku })
            {
                if (!overridesBySku.ContainsKey(thisSku))
                    overridesBySku[thisSku] = new OverrideSet(
                        new HashSet<string>(StringComparer.OrdinalIgnoreCase),
                        new HashSet<string>(StringComparer.OrdinalIgnoreCase));

                var otherSku = string.Equals(o.BaseSku, thisSku, StringComparison.OrdinalIgnoreCase)
                    ? o.CompatibleSku : o.BaseSku;

                if (string.Equals(o.OverrideType, "whitelist", StringComparison.OrdinalIgnoreCase))
                    overridesBySku[thisSku].Whitelisted.Add(otherSku);
                else if (string.Equals(o.OverrideType, "blacklist", StringComparison.OrdinalIgnoreCase))
                    overridesBySku[thisSku].Blacklisted.Add(otherSku);
            }
        }

        // Only base-type products are computed — all others derive their results
        // from the reverse direction of these stored forward pairs.
        var productsToProcess = skuSet
            .Where(s => bySku.ContainsKey(s))
            .Select(s => bySku[s])
            .Where(p => BaseCategories.Contains(p.Category))
            .ToList();

        if (productsToProcess.Count == 0) return 0;

        var baseProductIds = productsToProcess.Select(p => p.Id).ToList();

        // Delete existing forward records for these base products only.
        var existingRecords = await _db.ProductCompatibilities
            .Where(pc => baseProductIds.Contains(pc.BaseProductId))
            .ToListAsync();
        _db.ProductCompatibilities.RemoveRange(existingRecords);

        var pairMap = new Dictionary<(int, int), ProductCompatibility>();
        int processed = 0;

        foreach (var product in productsToProcess)
        {
            var candidateCategories = GetCandidateCategories(product.Category);
            var candidatesByCategory = candidateCategories
                .Where(c => byCategory.ContainsKey(c))
                .ToDictionary(c => c, c => byCategory[c]);

            var results = _engine.FindCompatibleProducts(product, candidatesByCategory);

            overridesBySku.TryGetValue(product.Sku, out var overrideSet);
            overrideSet ??= new OverrideSet(
                new HashSet<string>(StringComparer.OrdinalIgnoreCase),
                new HashSet<string>(StringComparer.OrdinalIgnoreCase));
            results = ApplyOverrides(results, overrideSet);

            foreach (var category in results)
            {
                foreach (var compatible in category.Products)
                {
                    if (!bySku.TryGetValue(compatible.Sku, out var compatProduct))
                        continue;

                    var forwardKey = (product.Id, compatProduct.Id);
                    if (!pairMap.ContainsKey(forwardKey))
                        pairMap[forwardKey] = new ProductCompatibility
                        {
                            BaseProductId = product.Id,
                            CompatibleProductId = compatProduct.Id,
                            MatchReason = compatible.MatchReason ?? category.Category,
                            ComputedAt = DateTime.UtcNow
                        };
                }

                if (!string.IsNullOrEmpty(category.IncompatibilityReason))
                {
                    var selfKey = (product.Id, product.Id);
                    if (!pairMap.ContainsKey(selfKey))
                        pairMap[selfKey] = new ProductCompatibility
                        {
                            BaseProductId = product.Id,
                            CompatibleProductId = product.Id,
                            IncompatibilityReason = category.IncompatibilityReason,
                            ComputedAt = DateTime.UtcNow
                        };
                }
            }

            processed++;

            if (onProgress != null && processed % 50 == 0)
            {
                try { await onProgress(processed); } catch { /* non-fatal */ }
            }
        }

        var newRecords = pairMap.Values.ToList();

        // Bulk insert in chunks to avoid parameter limit
        const int chunkSize = 500;
        for (int i = 0; i < newRecords.Count; i += chunkSize)
        {
            _db.ProductCompatibilities.AddRange(newRecords.Skip(i).Take(chunkSize));
            await _db.SaveChangesAsync();
        }

        if (newRecords.Count == 0)
            await _db.SaveChangesAsync(); // flush the deletes

        _logger.LogInformation("Bulk compatibility: processed {Count} products, {Records} compatibility records ({Bidirectional} bidirectional pairs)",
            processed, newRecords.Count, newRecords.Count / 2);

        return processed;
    }

    private async Task<List<CompatibilityCategoryResult>?> LoadPrecomputedCompatibilitiesAsync(int baseProductId)
    {
        // Forward: rows where this product is the base
        var forwardRows = await _db.ProductCompatibilities
            .AsNoTracking()
            .Where(pc => pc.BaseProductId == baseProductId
                && (pc.IncompatibilityReason == null || pc.IncompatibilityReason == ""))
            .Include(pc => pc.CompatibleProduct)
            .ToListAsync();

        // Reverse: rows where this product was listed as compatible by another product
        var reverseRows = await _db.ProductCompatibilities
            .AsNoTracking()
            .Where(pc => pc.CompatibleProductId == baseProductId
                && (pc.IncompatibilityReason == null || pc.IncompatibilityReason == ""))
            .Include(pc => pc.BaseProduct)
            .ToListAsync();

        if (forwardRows.Count == 0 && reverseRows.Count == 0)
            return null;

        // Check overrides
        var baseSku = await _db.Products.Where(p => p.Id == baseProductId)
            .Select(p => p.Sku).FirstAsync();
        var overrides = await LoadOverridesAsync(baseSku);

        var byCategory = new Dictionary<string, List<CompatibleProductDto>>();
        var seenSkus = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Forward rows: CompatibleProduct is the target
        foreach (var row in forwardRows)
        {
            var compatSku = row.CompatibleProduct.Sku;
            if (string.Equals(compatSku, baseSku, StringComparison.OrdinalIgnoreCase)) continue; // skip self
            if (overrides.Blacklisted.Contains(compatSku)) continue;
            if (!seenSkus.Add(compatSku)) continue;

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
                MatchReason = row.MatchReason
            });
        }

        // Reverse rows: BaseProduct is the target (if base A computed B as compatible, B can find A here)
        foreach (var row in reverseRows)
        {
            var compatSku = row.BaseProduct.Sku;
            if (string.Equals(compatSku, baseSku, StringComparison.OrdinalIgnoreCase)) continue; // skip self
            if (overrides.Blacklisted.Contains(compatSku)) continue;
            if (!seenSkus.Add(compatSku)) continue;

            var category = row.BaseProduct.Category;
            if (!byCategory.ContainsKey(category))
                byCategory[category] = new List<CompatibleProductDto>();

            byCategory[category].Add(new CompatibleProductDto
            {
                Sku = compatSku,
                Name = row.BaseProduct.ProductName,
                Brand = row.BaseProduct.Brand,
                Series = row.BaseProduct.Series,
                Family = row.BaseProduct.Family,
                Category = category,
                ImageUrl = row.BaseProduct.ImageUrl,
                ProductPageUrl = row.BaseProduct.ProductPageUrl,
                MatchReason = row.MatchReason
            });
        }

        // Add whitelisted products that aren't already in results
        foreach (var whitelistedSku in overrides.Whitelisted)
        {
            if (seenSkus.Contains(whitelistedSku)) continue;

            var whitelistedProduct = await _db.Products.AsNoTracking()
                .FirstOrDefaultAsync(p => p.Sku == whitelistedSku);
            if (whitelistedProduct == null) continue;

            seenSkus.Add(whitelistedSku);
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
                MatchReason = "Whitelisted"
            });
        }

        var precomputedResults = byCategory.Select(kvp => new CompatibilityCategoryResult
        {
            Category = kvp.Key,
            Products = kvp.Value
        }).ToList();

        return PruneOrphanedReturnPanels(precomputedResults);
    }

    private async Task<List<CompatibilityCategoryResult>> ComputeOnDemandAsync(Product product)
    {
        // Determine which candidate categories are needed
        var candidateCategories = GetCandidateCategories(product.Category);

        // No on-demand rules for this category — compatibility comes from pre-computed data only
        if (candidateCategories.Length == 0)
            return new List<CompatibilityCategoryResult>();

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
        // Only forward records are stored (base → compatible).
        // Reverse lookups are handled at query time by reading WHERE compatible_product_id = X.
        var existing = await _db.ProductCompatibilities
            .Where(pc => pc.BaseProductId == baseProduct.Id)
            .ToListAsync();

        _db.ProductCompatibilities.RemoveRange(existing);

        var skus = categories
            .SelectMany(c => c.Products)
            .Select(p => p.Sku)
            .Distinct()
            .ToList();

        var productsMap = await _db.Products
            .Where(p => skus.Contains(p.Sku))
            .ToDictionaryAsync(p => p.Sku, p => p);

        var pairMap = new Dictionary<(int, int), ProductCompatibility>();

        foreach (var category in categories)
        {
            foreach (var compatible in category.Products)
            {
                if (!productsMap.TryGetValue(compatible.Sku, out var compatProduct))
                    continue;

                var fwd = (baseProduct.Id, compatProduct.Id);
                if (!pairMap.ContainsKey(fwd))
                    pairMap[fwd] = new ProductCompatibility
                    {
                        BaseProductId = baseProduct.Id,
                        CompatibleProductId = compatProduct.Id,
                        MatchReason = compatible.MatchReason ?? category.Category,
                        ComputedAt = DateTime.UtcNow
                    };
            }

            if (!string.IsNullOrEmpty(category.IncompatibilityReason))
            {
                var self = (baseProduct.Id, baseProduct.Id);
                if (!pairMap.ContainsKey(self))
                    pairMap[self] = new ProductCompatibility
                    {
                        BaseProductId = baseProduct.Id,
                        CompatibleProductId = baseProduct.Id,
                        IncompatibilityReason = category.IncompatibilityReason,
                        ComputedAt = DateTime.UtcNow
                    };
            }
        }

        _db.ProductCompatibilities.AddRange(pairMap.Values);
        await _db.SaveChangesAsync();
    }

    public async Task ClearAllCompatibilitiesAsync()
    {
        await _db.Database.ExecuteSqlRawAsync("TRUNCATE TABLE product_compatibility");
    }

    // Only base-type categories are computed forward. All other categories
    // (doors, screens, walls, enclosures, return panels) find their compatible
    // products by querying the reverse direction of these stored pairs.
    private static readonly HashSet<string> BaseCategories = new(StringComparer.OrdinalIgnoreCase)
    {
        CompatibilityConstants.Categories.ShowerBases,
        CompatibilityConstants.Categories.Bathtubs,
        CompatibilityConstants.Categories.Showers,
        CompatibilityConstants.Categories.TubShowers
    };

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

        // A Return Panel is only valid when paired with a same-family Shower Door.
        // After blacklisting a door, prune any panels whose family has no surviving door.
        return PruneOrphanedReturnPanels(results);
    }

    /// <summary>
    /// Removes Return Panels that have no surviving Shower Door in the same family.
    /// Panels are only meaningful when a compatible door of the same family exists.
    /// </summary>
    private static List<CompatibilityCategoryResult> PruneOrphanedReturnPanels(
        List<CompatibilityCategoryResult> results)
    {
        var panelCat = results.FirstOrDefault(r =>
            r.Category == CompatibilityConstants.Categories.ReturnPanels);

        if (panelCat == null || panelCat.Products.Count == 0)
            return results;

        var doorCat = results.FirstOrDefault(r =>
            r.Category == CompatibilityConstants.Categories.ShowerDoors);

        var survivingDoorFamilies = doorCat?.Products
            .Where(d => !string.IsNullOrEmpty(d.Family))
            .Select(d => d.Family!)
            .ToHashSet(StringComparer.OrdinalIgnoreCase)
            ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        panelCat.Products = panelCat.Products
            .Where(p => !string.IsNullOrEmpty(p.Family)
                        && survivingDoorFamilies.Contains(p.Family!))
            .ToList();

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

    /// <summary>
    /// Progressively strips trailing "-xxx" segments from a configuration SKU to find
    /// the matching base product. For example, "410006-501-001" tries "410006-501"
    /// then "410006", returning the first one found in the DB.
    /// </summary>
    private async Task<Product?> TryFindByStrippedSkuAsync(string sku)
    {
        var candidate = sku;
        while (candidate.Contains('-'))
        {
            candidate = candidate[..candidate.LastIndexOf('-')];
            var found = await _productService.GetBySkuAsync(candidate);
            if (found != null) return found;
        }
        return null;
    }
}
