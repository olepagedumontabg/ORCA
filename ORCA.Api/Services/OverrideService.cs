using ClosedXML.Excel;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services.Interface;
using System.Text;

namespace ORCA.Api.Services;

public class OverrideService : IOverrideService
{
    private readonly OrcaDbContext _db;

    public OverrideService(OrcaDbContext db)
    {
        _db = db;
    }

    // ── SKU resolution ────────────────────────────────────────────────────
    // Overrides use EXACT SKU matching. The overrides autocomplete calls
    // /suggest?exact=true which returns real DB SKUs (no base-SKU stripping),
    // so the value the user picks will always match a real product row.

    private Task<bool> SkuExistsAsync(string sku) =>
        _db.Products.AnyAsync(p => p.Sku == sku);

    // ── List ──────────────────────────────────────────────────────────────

    public async Task<List<OverrideDto>> ListAsync(string? sku = null)
    {
        var query = _db.CompatibilityOverrides.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(sku))
        {
            var upper = sku.Trim().ToUpper();
            query = query.Where(o => o.BaseSku == upper || o.CompatibleSku == upper);
        }

        // Load override rows first, then batch-fetch product names in one query.
        // Avoids correlated sub-selects that EF Core / Npgsql may not translate.
        var rows = await query
            .OrderByDescending(o => o.CreatedAt)
            .ToListAsync();

        var allSkus = rows
            .SelectMany(r => new[] { r.BaseSku, r.CompatibleSku })
            .Distinct()
            .ToList();

        var nameMap = await _db.Products.AsNoTracking()
            .Where(p => allSkus.Contains(p.Sku))
            .ToDictionaryAsync(p => p.Sku, p => p.ProductName);

        return rows.Select(r => new OverrideDto(
            r.Id,
            r.BaseSku,
            nameMap.GetValueOrDefault(r.BaseSku),
            r.CompatibleSku,
            nameMap.GetValueOrDefault(r.CompatibleSku),
            r.OverrideType,
            r.Reason,
            r.CreatedAt,
            r.CreatedBy
        )).ToList();
    }

    // ── Create ────────────────────────────────────────────────────────────

    public async Task<OverrideCreateResult> CreateAsync(
        string baseSku, string compatibleSku, string overrideType, string? reason, string? createdBy)
    {
        baseSku       = baseSku.Trim().ToUpper();
        compatibleSku = compatibleSku.Trim().ToUpper();
        var type      = overrideType.Trim().ToLower();

        if (string.IsNullOrWhiteSpace(baseSku))
            return Fail(400, "baseSku is required.");
        if (string.IsNullOrWhiteSpace(compatibleSku))
            return Fail(400, "compatibleSku is required.");
        if (type != "whitelist" && type != "blacklist")
            return Fail(400, "overrideType must be 'whitelist' or 'blacklist'.");
        if (string.Equals(baseSku, compatibleSku, StringComparison.OrdinalIgnoreCase))
            return Fail(400, "baseSku and compatibleSku cannot be the same product.");

        if (!await SkuExistsAsync(baseSku))
            return Fail(400, $"Product not found: '{baseSku}'. Make sure the SKU exists in the product catalog.");
        if (!await SkuExistsAsync(compatibleSku))
            return Fail(400, $"Product not found: '{compatibleSku}'. Make sure the SKU exists in the product catalog.");

        var existing = await _db.CompatibilityOverrides
            .Where(o => (o.BaseSku == baseSku   && o.CompatibleSku == compatibleSku) ||
                        (o.BaseSku == compatibleSku && o.CompatibleSku == baseSku))
            .Select(o => new { o.OverrideType })
            .FirstOrDefaultAsync();

        if (existing != null)
        {
            return existing.OverrideType == type
                ? Fail(409, $"A {type} override for {baseSku} ↔ {compatibleSku} already exists.")
                : Fail(409, $"An override for {baseSku} ↔ {compatibleSku} already exists as '{existing.OverrideType}'. Delete it first before adding a {type} override.");
        }

        var entry = new CompatibilityOverride
        {
            BaseSku       = baseSku,
            CompatibleSku = compatibleSku,
            OverrideType  = type,
            Reason        = string.IsNullOrWhiteSpace(reason) ? null : reason.Trim(),
            CreatedAt     = DateTime.UtcNow,
            CreatedBy     = createdBy
        };

        _db.CompatibilityOverrides.Add(entry);
        await _db.SaveChangesAsync();

        return new OverrideCreateResult(
            Success:    true,
            Error:      null,
            StatusCode: 200,
            Override:   new OverrideCreatedDto(
                entry.Id, entry.BaseSku, entry.CompatibleSku,
                entry.OverrideType, entry.Reason, entry.CreatedAt)
        );
    }

    private static OverrideCreateResult Fail(int status, string error) =>
        new(false, error, status);

    // ── Delete ────────────────────────────────────────────────────────────

    public async Task<OverrideDeleteResult> DeleteAsync(int id)
    {
        var entry = await _db.CompatibilityOverrides.FindAsync(id);
        if (entry == null)
            return new OverrideDeleteResult(false, $"Override {id} not found.", 404);

        _db.CompatibilityOverrides.Remove(entry);
        await _db.SaveChangesAsync();

        return new OverrideDeleteResult(
            true,
            $"Override {id} deleted ({entry.OverrideType}: {entry.BaseSku} ↔ {entry.CompatibleSku})",
            200);
    }

    // ── Import ────────────────────────────────────────────────────────────

    public async Task<OverrideImportResult> ImportAsync(IFormFile file, string? createdBy)
    {
        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();

        List<RawRow> rawRows;
        try
        {
            rawRows = ext == ".xlsx" ? ParseXlsx(file) : ParseCsv(file);
        }
        catch (Exception ex)
        {
            return new OverrideImportResult(false, 0, 0, [], 1,
                [new OverrideErrorRow(0, "", "", "", [$"Could not parse file: {ex.Message}"])]);
        }

        if (rawRows.Count == 0)
            return new OverrideImportResult(false, 0, 0, [], 1,
                [new OverrideErrorRow(0, "", "", "", ["The file contains no data rows."])]);

        // Batch-resolve SKU existence — one query per unique SKU (import files are small)
        var uniqueSkus = rawRows
            .SelectMany(r => new[] { r.BaseSku, r.CompatibleSku })
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Select(s => s!.Trim().ToUpper())
            .Distinct()
            .ToList();

        var resolvedSkus = new HashSet<string>(StringComparer.Ordinal);
        foreach (var sku in uniqueSkus)
        {
            if (await SkuExistsAsync(sku))
                resolvedSkus.Add(sku);
        }

        // Validate rows
        var validRows  = new List<ValidRow>();
        var errors     = new List<OverrideErrorRow>();
        var rowMsgs    = new List<string>();

        for (int i = 0; i < rawRows.Count; i++)
        {
            var r      = rawRows[i];
            var rowNum = i + 2; // 1-based + header
            rowMsgs.Clear();

            var baseSku   = r.BaseSku?.Trim().ToUpper()      ?? "";
            var compatSku = r.CompatibleSku?.Trim().ToUpper() ?? "";
            var typeRaw   = r.Type?.Trim()                    ?? "";
            var reason    = string.IsNullOrWhiteSpace(r.Reason) ? null : r.Reason.Trim();

            if (string.IsNullOrWhiteSpace(baseSku) && string.IsNullOrWhiteSpace(compatSku) && string.IsNullOrWhiteSpace(typeRaw))
                continue; // blank row

            if (string.IsNullOrWhiteSpace(baseSku))
                rowMsgs.Add("Base SKU is missing.");
            else if (!resolvedSkus.Contains(baseSku))
                rowMsgs.Add($"Base SKU '{baseSku}' was not found in the product catalog.");

            if (string.IsNullOrWhiteSpace(compatSku))
                rowMsgs.Add("Compatible SKU is missing.");
            else if (!resolvedSkus.Contains(compatSku))
                rowMsgs.Add($"Compatible SKU '{compatSku}' was not found in the product catalog.");

            if (!string.IsNullOrWhiteSpace(baseSku) && !string.IsNullOrWhiteSpace(compatSku) &&
                string.Equals(baseSku, compatSku, StringComparison.OrdinalIgnoreCase))
                rowMsgs.Add("Base SKU and Compatible SKU cannot be the same product.");

            var typeLower = typeRaw.ToLower();
            if (string.IsNullOrWhiteSpace(typeRaw))
                rowMsgs.Add("Type is missing. It must be 'Whitelist' or 'Blacklist'.");
            else if (typeLower != "whitelist" && typeLower != "blacklist")
                rowMsgs.Add($"Type '{typeRaw}' is invalid. It must be 'Whitelist' or 'Blacklist'.");

            if (rowMsgs.Count > 0)
            {
                errors.Add(new OverrideErrorRow(rowNum, baseSku, compatSku, typeRaw, [..rowMsgs]));
                continue;
            }

            validRows.Add(new ValidRow(baseSku, compatSku, typeLower, reason, rowNum));
        }

        // Insert valid rows, skip duplicates
        var imported = 0;
        var skipped  = new List<OverrideSkippedRow>();

        foreach (var row in validRows)
        {
            var existing = await _db.CompatibilityOverrides
                .Where(o => (o.BaseSku == row.BaseSku   && o.CompatibleSku == row.CompatibleSku) ||
                            (o.BaseSku == row.CompatibleSku && o.CompatibleSku == row.BaseSku))
                .Select(o => new { o.OverrideType })
                .FirstOrDefaultAsync();

            if (existing != null)
            {
                var reason = existing.OverrideType == row.Type
                    ? $"A {row.Type} override for {row.BaseSku} ↔ {row.CompatibleSku} already exists."
                    : $"An override for {row.BaseSku} ↔ {row.CompatibleSku} already exists as '{existing.OverrideType}'. Delete it first.";

                skipped.Add(new OverrideSkippedRow(row.RowNumber, row.BaseSku, row.CompatibleSku, reason));
                continue;
            }

            _db.CompatibilityOverrides.Add(new CompatibilityOverride
            {
                BaseSku       = row.BaseSku,
                CompatibleSku = row.CompatibleSku,
                OverrideType  = row.Type,
                Reason        = row.Reason,
                CreatedAt     = DateTime.UtcNow,
                CreatedBy     = createdBy
            });
            imported++;
        }

        if (imported > 0)
            await _db.SaveChangesAsync();

        return new OverrideImportResult(
            Success:        errors.Count == 0,
            Imported:       imported,
            Skipped:        skipped.Count,
            SkippedDetails: skipped,
            ErrorCount:     errors.Count,
            Errors:         errors
        );
    }

    // ── Template ──────────────────────────────────────────────────────────

    public byte[] GetImportTemplateCsv()
    {
        var csv = new StringBuilder();
        csv.AppendLine("Base SKU,Compatible SKU,Type,Reason (Optional)");
        csv.AppendLine("100959,220333,Whitelist,Confirmed compatible by engineering");
        csv.AppendLine("420000,999999,Blacklist,");
        return Encoding.UTF8.GetBytes(csv.ToString());
    }

    // ── File parsers ──────────────────────────────────────────────────────

    private static List<RawRow> ParseXlsx(IFormFile file)
    {
        using var stream = file.OpenReadStream();
        using var wb     = new XLWorkbook(stream);
        var ws      = wb.Worksheets.First();
        var lastCol = ws.Row(1).LastCellUsed()?.Address.ColumnNumber ?? 10;
        var colMap  = MapColumns(Enumerable.Range(1, lastCol)
            .Select(c => (c, ws.Row(1).Cell(c).GetString().Trim()))
            .ToList());

        var rows    = new List<RawRow>();
        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;

        for (int r = 2; r <= lastRow; r++)
        {
            string? Get(string key) =>
                colMap.TryGetValue(key, out var ci) ? ws.Row(r).Cell(ci).GetString().Trim() : null;

            rows.Add(new RawRow(
                Get("base sku"), Get("compatible sku"), Get("type"),
                Get("reason (optional)") ?? Get("reason")));
        }

        return rows;
    }

    private static List<RawRow> ParseCsv(IFormFile file)
    {
        using var reader = new StreamReader(file.OpenReadStream(), Encoding.UTF8);
        var lines = new List<string>();
        string? line;
        while ((line = reader.ReadLine()) != null)
            lines.Add(line);

        if (lines.Count == 0) throw new InvalidDataException("File is empty.");

        var headers = SplitCsvLine(lines[0]);
        var colMap  = MapColumns(headers.Select((h, i) => (i + 1, h.Trim())).ToList());

        var rows = new List<RawRow>();
        for (int i = 1; i < lines.Count; i++)
        {
            var cells = SplitCsvLine(lines[i]);
            string? Get(string key) =>
                colMap.TryGetValue(key, out var idx) && idx <= cells.Count
                    ? cells[idx - 1].Trim() : null;

            rows.Add(new RawRow(
                Get("base sku"), Get("compatible sku"), Get("type"),
                Get("reason (optional)") ?? Get("reason")));
        }
        return rows;
    }

    private static Dictionary<string, int> MapColumns(List<(int Index, string Header)> cols)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var (idx, header) in cols)
        {
            var key = header.ToLower().Trim();
            if (!string.IsNullOrWhiteSpace(key) && !map.ContainsKey(key))
                map[key] = idx;
        }
        return map;
    }

    private static List<string> SplitCsvLine(string line)
    {
        var fields  = new List<string>();
        var current = new StringBuilder();
        bool inQuotes = false;

        for (int i = 0; i < line.Length; i++)
        {
            char ch = line[i];
            if (inQuotes)
            {
                if (ch == '"' && i + 1 < line.Length && line[i + 1] == '"')
                { current.Append('"'); i++; }
                else if (ch == '"') inQuotes = false;
                else current.Append(ch);
            }
            else
            {
                if (ch == '"')      inQuotes = true;
                else if (ch == ',') { fields.Add(current.ToString()); current.Clear(); }
                else current.Append(ch);
            }
        }
        fields.Add(current.ToString());
        return fields;
    }

    private record RawRow(string? BaseSku, string? CompatibleSku, string? Type, string? Reason);
    private record ValidRow(string BaseSku, string CompatibleSku, string Type, string? Reason, int RowNumber);
}
