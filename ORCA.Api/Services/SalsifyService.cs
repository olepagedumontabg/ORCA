using ClosedXML.Excel;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services.Interface;
using System.Text.Json;

namespace ORCA.Api.Services;

public class SalsifyService : ISalsifyService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly HttpClient _httpClient;
    private readonly ILogger<SalsifyService> _logger;

    private static readonly HashSet<string> ExcludeColumns = new(StringComparer.OrdinalIgnoreCase)
    {
        "Unique ID", "Product Name", "Brand", "Series", "Family",
        "Length", "Width", "Height", "Nominal Dimensions",
        "Product Page URL", "Image URL", "Ranking",
        "Alternate ID 1", "Alternate ID 2", "Alternate ID 3"
    };

    public SalsifyService(
        IServiceScopeFactory scopeFactory,
        HttpClient httpClient,
        ILogger<SalsifyService> logger)
    {
        _scopeFactory = scopeFactory;
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<SalsifyWebhookResult> ProcessWebhookAsync(
        string productFeedUrl, string? channelId, string? channelName)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<OrcaDbContext>();

        var syncRecord = new SyncStatus
        {
            SyncType = "salsify_webhook",
            Status = "queued",
            StartedAt = DateTime.UtcNow,
            SyncMetadata = JsonSerializer.Serialize(new
            {
                channel_id = channelId,
                channel_name = channelName,
                product_feed_url = productFeedUrl
            })
        };

        db.SyncStatuses.Add(syncRecord);
        await db.SaveChangesAsync();
        var syncId = syncRecord.Id;

        _ = Task.Run(async () => await RunSyncAsync(syncId, productFeedUrl));

        return new SalsifyWebhookResult(true, "Webhook queued for processing", syncId);
    }

    private async Task RunSyncAsync(int syncId, string productFeedUrl)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<OrcaDbContext>();
        var compatibilityService = scope.ServiceProvider.GetRequiredService<ICompatibilityService>();

        SyncStatus? syncRecord = null;
        var step = "initializing";

        try
        {
            syncRecord = await db.SyncStatuses.FindAsync(syncId);
            if (syncRecord == null) return;

            step = "updating status to running";
            syncRecord.Status = "running";
            await db.SaveChangesAsync();

            step = "downloading Excel file from Salsify";
            _logger.LogInformation("Downloading Excel from: {Url}", productFeedUrl);
            var excelBytes = await _httpClient.GetByteArrayAsync(productFeedUrl);

            if (excelBytes.Length == 0)
                throw new InvalidOperationException("The downloaded file is empty (0 bytes). The product feed URL may be expired or invalid.");

            step = $"parsing Excel file ({excelBytes.Length:N0} bytes)";
            _logger.LogInformation("Parsing Excel ({Size} bytes)", excelBytes.Length);
            var (added, updated, deleted, changedSkus) = await SyncFromExcelBytesAsync(db, excelBytes);

            step = "recomputing product compatibilities";
            _logger.LogInformation("Recomputing compatibilities for {Count} changed products", changedSkus.Count);
            int compatCount = await compatibilityService.BulkComputeCompatibilitiesAsync(changedSkus);

            step = "saving final sync results";
            syncRecord = await db.SyncStatuses.FindAsync(syncId);
            if (syncRecord != null)
            {
                syncRecord.Status = "completed";
                syncRecord.CompletedAt = DateTime.UtcNow;
                syncRecord.ProductsAdded = added;
                syncRecord.ProductsUpdated = updated;
                syncRecord.ProductsDeleted = deleted;
                syncRecord.CompatibilitiesUpdated = compatCount;
                await db.SaveChangesAsync();
            }

            _logger.LogInformation("Sync #{SyncId} complete: +{Added} ~{Updated} -{Deleted} comps:{Compat}",
                syncId, added, updated, deleted, compatCount);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Sync #{SyncId} failed at step [{Step}]", syncId, step);

            try
            {
                if (syncRecord == null)
                    syncRecord = await db.SyncStatuses.FindAsync(syncId);

                if (syncRecord != null)
                {
                    syncRecord.Status = "failed";
                    syncRecord.CompletedAt = DateTime.UtcNow;
                    syncRecord.ErrorMessage = $"[{step}] {ex.Message}";
                    await db.SaveChangesAsync();
                }
            }
            catch (Exception inner)
            {
                _logger.LogError(inner, "Failed to update sync status to failed");
            }
        }
    }

    private async Task<(int Added, int Updated, int Deleted, HashSet<string> ChangedSkus)>
        SyncFromExcelBytesAsync(OrcaDbContext db, byte[] excelBytes)
    {
        using var stream = new MemoryStream(excelBytes);
        using var workbook = new XLWorkbook(stream);

        // Load ALL existing products into memory once — avoids N+1 per-row queries
        var existingProductsMap = await db.Products
            .ToDictionaryAsync(p => p.Sku, p => p, StringComparer.OrdinalIgnoreCase);
        var existingSkus = existingProductsMap.Keys.ToHashSet(StringComparer.OrdinalIgnoreCase);

        var excelSkus = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var changedSkus = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        int added = 0, updated = 0;

        foreach (var worksheet in workbook.Worksheets)
        {
            var category = worksheet.Name.Trim();
            if (string.IsNullOrWhiteSpace(category)) continue;

            var headerRow = worksheet.Row(1);
            var headers = new Dictionary<int, string>();

            foreach (var cell in headerRow.CellsUsed())
                headers[cell.Address.ColumnNumber] = cell.GetValue<string>().Trim();

            if (!headers.ContainsValue("Unique ID")) continue;

            int skuCol = headers.First(h => h.Value == "Unique ID").Key;

            _logger.LogInformation("Syncing category: {Category}", category);

            foreach (var row in worksheet.RowsUsed().Skip(1))
            {
                var skuRaw = row.Cell(skuCol).GetValue<string>()?.Trim()?.ToUpperInvariant();
                if (string.IsNullOrWhiteSpace(skuRaw) || skuRaw == "NAN") continue;

                excelSkus.Add(skuRaw);

                var productData = ExtractProductData(row, headers, skuRaw, category);
                var attrsJson = BuildAttributesJson(row, headers);

                existingProductsMap.TryGetValue(skuRaw, out var existing);

                if (existing != null)
                {
                    var (changed, dimensionsChanged) = UpdateProduct(existing, productData, attrsJson);
                    if (changed)
                    {
                        existing.UpdatedAt = DateTime.UtcNow;
                        updated++;
                    }
                    if (dimensionsChanged)
                        changedSkus.Add(skuRaw);
                }
                else
                {
                    var product = new Product
                    {
                        Sku = productData.Sku,
                        ProductName = productData.ProductName,
                        Brand = productData.Brand,
                        Series = productData.Series,
                        Family = productData.Family,
                        Category = productData.Category,
                        Length = productData.Length,
                        Width = productData.Width,
                        Height = productData.Height,
                        NominalDimensions = productData.NominalDimensions,
                        ProductPageUrl = productData.ProductPageUrl,
                        ImageUrl = productData.ImageUrl,
                        Ranking = productData.Ranking,
                        AlternateId1 = productData.AlternateId1,
                        AlternateId2 = productData.AlternateId2,
                        AlternateId3 = productData.AlternateId3,
                        Attributes = attrsJson,
                        CreatedAt = DateTime.UtcNow,
                        UpdatedAt = DateTime.UtcNow
                    };
                    db.Products.Add(product);
                    existingProductsMap[skuRaw] = product; // track so duplicate SKUs in other worksheets update rather than re-add
                    added++;
                    changedSkus.Add(skuRaw); // new product always triggers compat recompute
                }
            }

            await db.SaveChangesAsync();
        }

        var toDeleteSkus = existingSkus.Except(excelSkus).ToList();
        int deleted = 0;
        if (toDeleteSkus.Count > 0)
        {
            _logger.LogInformation("Removing {Count} products no longer in Excel", toDeleteSkus.Count);
            var stale = await db.Products
                .Where(p => toDeleteSkus.Contains(p.Sku))
                .ToListAsync();
            db.Products.RemoveRange(stale);
            await db.SaveChangesAsync();
            deleted = toDeleteSkus.Count;
        }

        return (added, updated, deleted, changedSkus);
    }

    private static (string Sku, string? ProductName, string? Brand, string? Series, string? Family,
        string Category, decimal? Length, decimal? Width, decimal? Height,
        string? NominalDimensions, string? ProductPageUrl, string? ImageUrl, int? Ranking,
        string? AlternateId1, string? AlternateId2, string? AlternateId3)
        ExtractProductData(IXLRow row, Dictionary<int, string> headers, string sku, string category)
    {
        T? Get<T>(string name) where T : struct
        {
            var col = headers.FirstOrDefault(h => h.Value == name).Key;
            if (col == 0) return null;
            var cell = row.Cell(col);
            if (cell.IsEmpty()) return null;
            try { return cell.GetValue<T>(); } catch { return null; }
        }

        string? GetStr(string name)
        {
            var col = headers.FirstOrDefault(h => h.Value == name).Key;
            if (col == 0) return null;
            var cell = row.Cell(col);
            if (cell.IsEmpty()) return null;
            var val = cell.GetValue<string>()?.Trim();
            return string.IsNullOrEmpty(val) ? null : val;
        }

        return (
            sku,
            GetStr("Product Name"),
            GetStr("Brand"),
            GetStr("Series"),
            GetStr("Family"),
            category,
            Get<decimal>("Length"),
            Get<decimal>("Width"),
            Get<decimal>("Height"),
            GetStr("Nominal Dimensions"),
            GetStr("Product Page URL"),
            GetStr("Image URL"),
            Get<int>("Ranking"),
            GetStr("Alternate ID 1"),
            GetStr("Alternate ID 2"),
            GetStr("Alternate ID 3")
        );
    }

    private static string? BuildAttributesJson(IXLRow row, Dictionary<int, string> headers)
    {
        var attrs = new Dictionary<string, object?>();

        foreach (var (col, name) in headers)
        {
            if (ExcludeColumns.Contains(name)) continue;

            var cell = row.Cell(col);
            if (cell.IsEmpty()) continue;

            var cellType = cell.DataType;
            object? value = cellType switch
            {
                XLDataType.Number => cell.GetValue<double>(),
                XLDataType.Boolean => cell.GetValue<bool>(),
                _ => cell.GetValue<string>()?.Trim()
            };

            if (value is string s && string.IsNullOrWhiteSpace(s)) continue;
            if (value != null) attrs[name] = value;
        }

        return attrs.Count > 0 ? JsonSerializer.Serialize(attrs) : null;
    }

    private static (bool Changed, bool DimensionsChanged) UpdateProduct(Product product,
        (string Sku, string? ProductName, string? Brand, string? Series, string? Family,
        string Category, decimal? Length, decimal? Width, decimal? Height,
        string? NominalDimensions, string? ProductPageUrl, string? ImageUrl, int? Ranking,
        string? AlternateId1, string? AlternateId2, string? AlternateId3) data,
        string? attrsJson)
    {
        bool changed = false;
        bool dimensionsChanged = false;

        if (product.Length != data.Length) { product.Length = data.Length; changed = true; dimensionsChanged = true; }
        if (product.Width != data.Width) { product.Width = data.Width; changed = true; dimensionsChanged = true; }
        if (product.Height != data.Height) { product.Height = data.Height; changed = true; dimensionsChanged = true; }
        if (product.NominalDimensions != data.NominalDimensions) { product.NominalDimensions = data.NominalDimensions; changed = true; dimensionsChanged = true; }

        if (product.ProductName != data.ProductName) { product.ProductName = data.ProductName; changed = true; }
        if (product.Brand != data.Brand) { product.Brand = data.Brand; changed = true; }
        if (product.Series != data.Series) { product.Series = data.Series; changed = true; }
        if (product.Family != data.Family) { product.Family = data.Family; changed = true; }
        if (product.Category != data.Category) { product.Category = data.Category; changed = true; }
        if (product.ProductPageUrl != data.ProductPageUrl) { product.ProductPageUrl = data.ProductPageUrl; changed = true; }
        if (product.ImageUrl != data.ImageUrl) { product.ImageUrl = data.ImageUrl; changed = true; }
        if (product.Ranking != data.Ranking) { product.Ranking = data.Ranking; changed = true; }
        if (product.AlternateId1 != data.AlternateId1) { product.AlternateId1 = data.AlternateId1; changed = true; }
        if (product.AlternateId2 != data.AlternateId2) { product.AlternateId2 = data.AlternateId2; changed = true; }
        if (product.AlternateId3 != data.AlternateId3) { product.AlternateId3 = data.AlternateId3; changed = true; }
        if (product.Attributes != attrsJson) { product.Attributes = attrsJson; changed = true; }

        return (changed, dimensionsChanged);
    }

    public async Task<List<SyncStatusDto>> GetStatusAsync(int? syncId, int limit)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<OrcaDbContext>();

        IQueryable<SyncStatus> query = db.SyncStatuses.AsNoTracking();

        if (syncId.HasValue)
            query = query.Where(s => s.Id == syncId.Value);
        else
            query = query.OrderByDescending(s => s.StartedAt).Take(Math.Min(limit, 100));

        var records = await query.ToListAsync();

        return records.Select(s =>
        {
            object? meta = null;
            if (!string.IsNullOrEmpty(s.SyncMetadata))
            {
                try { meta = JsonSerializer.Deserialize<object>(s.SyncMetadata); } catch { }
            }

            return new SyncStatusDto(
                s.Id, s.SyncType, s.Status, s.StartedAt, s.CompletedAt,
                s.ProductsAdded, s.ProductsUpdated, s.ProductsDeleted,
                s.CompatibilitiesUpdated, s.ErrorMessage, meta);
        }).ToList();
    }

    public async Task<CleanupResult> CleanupAsync(int olderThanDays)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<OrcaDbContext>();

        var cutoff = DateTime.UtcNow.AddDays(-olderThanDays);
        var toDelete = await db.SyncStatuses
            .Where(s => s.StartedAt < cutoff
                && (s.Status == "completed" || s.Status == "failed"))
            .ToListAsync();

        db.SyncStatuses.RemoveRange(toDelete);
        await db.SaveChangesAsync();

        return new CleanupResult(true, toDelete.Count,
            $"Deleted {toDelete.Count} sync records older than {olderThanDays} days");
    }
}
