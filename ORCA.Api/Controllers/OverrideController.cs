using ClosedXML.Excel;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using System.Security.Claims;
using System.Text;

namespace ORCA.Api.Controllers;

/// <summary>
/// Manages compatibility overrides.
/// All endpoints require Auth0 login and the ORCA - Editor (or Admin) role.
/// API endpoints return JSON 401/403 so browser JS receives clean errors.
/// </summary>
[ApiController]
public class OverrideController : ControllerBase
{
    private readonly OrcaDbContext _db;

    public OverrideController(OrcaDbContext db)
    {
        _db = db;
    }

    /// <summary>
    /// Checks authentication + role. Returns null when the caller is authorised.
    /// </summary>
    private IActionResult? RequireOverrideAdmin()
    {
        if (User?.Identity?.IsAuthenticated != true)
            return Unauthorized(new { success = false, error = "Authentication required. Please log in at /overrides." });

        if (!User.IsInRole("ORCA - Editor") && !User.IsInRole("ORCA - Admin"))
            return StatusCode(403, new { success = false, error = "The 'ORCA - Editor' role (or higher) is required to manage overrides." });

        return null;
    }

    private string? CurrentUserEmail =>
        User?.FindFirst(ClaimTypes.Email)?.Value
        ?? User?.FindFirst("email")?.Value
        ?? User?.Identity?.Name;

    // ── GET /api/overrides ────────────────────────────────────────────────

    [HttpGet("api/overrides")]
    public async Task<IActionResult> List([FromQuery] string? sku = null)
    {
        var authError = RequireOverrideAdmin();
        if (authError != null) return authError;

        var query = _db.CompatibilityOverrides.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(sku))
        {
            var upper = sku.Trim().ToUpper();
            query = query.Where(o => o.BaseSku == upper || o.CompatibleSku == upper);
        }

        var overrides = await query
            .OrderByDescending(o => o.CreatedAt)
            .Select(o => new
            {
                o.Id,
                o.BaseSku,
                BaseProductName = _db.Products
                    .Where(p => p.Sku == o.BaseSku)
                    .Select(p => p.ProductName)
                    .FirstOrDefault(),
                o.CompatibleSku,
                CompatibleProductName = _db.Products
                    .Where(p => p.Sku == o.CompatibleSku)
                    .Select(p => p.ProductName)
                    .FirstOrDefault(),
                o.OverrideType,
                o.Reason,
                o.CreatedAt,
                o.CreatedBy
            })
            .ToListAsync();

        return Ok(new { success = true, count = overrides.Count, overrides });
    }

    // ── POST /api/overrides ───────────────────────────────────────────────

    [HttpPost("api/overrides")]
    public async Task<IActionResult> Create([FromBody] CreateOverrideRequest request)
    {
        var authError = RequireOverrideAdmin();
        if (authError != null) return authError;

        if (string.IsNullOrWhiteSpace(request.BaseSku))
            return BadRequest(new { success = false, error = "baseSku is required" });
        if (string.IsNullOrWhiteSpace(request.CompatibleSku))
            return BadRequest(new { success = false, error = "compatibleSku is required" });

        var type = request.OverrideType?.Trim().ToLower();
        if (type != "whitelist" && type != "blacklist")
            return BadRequest(new { success = false, error = "overrideType must be 'whitelist' or 'blacklist'" });

        var baseSku  = request.BaseSku.Trim().ToUpper();
        var compatSku = request.CompatibleSku.Trim().ToUpper();

        if (string.Equals(baseSku, compatSku, StringComparison.OrdinalIgnoreCase))
            return BadRequest(new { success = false, error = "baseSku and compatibleSku cannot be the same product" });

        var baseExists = await _db.Products.AnyAsync(p => p.Sku == baseSku);
        if (!baseExists)
            return BadRequest(new { success = false, error = $"Product not found: {baseSku}" });

        var compatExists = await _db.Products.AnyAsync(p => p.Sku == compatSku);
        if (!compatExists)
            return BadRequest(new { success = false, error = $"Product not found: {compatSku}" });

        var existing = await _db.CompatibilityOverrides
            .Where(o => (o.BaseSku == baseSku && o.CompatibleSku == compatSku) ||
                        (o.BaseSku == compatSku && o.CompatibleSku == baseSku))
            .Select(o => new { o.OverrideType })
            .FirstOrDefaultAsync();

        if (existing != null)
        {
            var existingType = existing.OverrideType;
            if (existingType == type)
                return Conflict(new { success = false, error = $"A {type} override for {baseSku} ↔ {compatSku} already exists" });
            else
                return Conflict(new { success = false, error = $"An override for {baseSku} ↔ {compatSku} already exists as {existingType}. Delete it first before adding a {type} override." });
        }

        var entry = new CompatibilityOverride
        {
            BaseSku       = baseSku,
            CompatibleSku = compatSku,
            OverrideType  = type,
            Reason        = string.IsNullOrWhiteSpace(request.Reason) ? null : request.Reason.Trim(),
            CreatedAt     = DateTime.UtcNow,
            CreatedBy     = CurrentUserEmail
        };

        _db.CompatibilityOverrides.Add(entry);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            success = true,
            message = $"{type} override created: {baseSku} ↔ {compatSku}",
            @override = new { entry.Id, entry.BaseSku, entry.CompatibleSku, entry.OverrideType, entry.Reason, entry.CreatedAt }
        });
    }

    // ── DELETE /api/overrides/{id} ────────────────────────────────────────

    [HttpDelete("api/overrides/{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var authError = RequireOverrideAdmin();
        if (authError != null) return authError;

        var entry = await _db.CompatibilityOverrides.FindAsync(id);
        if (entry == null)
            return NotFound(new { success = false, error = $"Override {id} not found" });

        _db.CompatibilityOverrides.Remove(entry);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            success = true,
            message = $"Override {id} deleted ({entry.OverrideType}: {entry.BaseSku} ↔ {entry.CompatibleSku})"
        });
    }

    // ── GET /api/overrides/import-template ────────────────────────────────

    /// <summary>
    /// Downloads a blank CSV template with the correct column headers.
    /// </summary>
    [HttpGet("api/overrides/import-template")]
    public IActionResult DownloadTemplate()
    {
        var authError = RequireOverrideAdmin();
        if (authError != null) return authError;

        var csv = new StringBuilder();
        csv.AppendLine("Base SKU,Compatible SKU,Type,Reason (Optional)");
        csv.AppendLine("100959,220333,Whitelist,Confirmed compatible by engineering");
        csv.AppendLine("420000,999999,Blacklist,");

        var bytes = Encoding.UTF8.GetBytes(csv.ToString());
        return File(bytes, "text/csv", "overrides-import-template.csv");
    }

    // ── POST /api/overrides/import ────────────────────────────────────────

    /// <summary>
    /// Bulk-imports overrides from an uploaded XLSX or CSV file.
    /// Expected columns (order-independent, case-insensitive header match):
    ///   Base SKU | Compatible SKU | Type | Reason (Optional)
    /// Returns a detailed result with per-row validation errors.
    /// </summary>
    [HttpPost("api/overrides/import")]
    [RequestSizeLimit(10 * 1024 * 1024)]
    public async Task<IActionResult> Import(IFormFile? file)
    {
        var authError = RequireOverrideAdmin();
        if (authError != null) return authError;

        if (file == null || file.Length == 0)
            return BadRequest(new { success = false, error = "No file uploaded." });

        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (ext != ".csv" && ext != ".xlsx")
            return BadRequest(new { success = false, error = "Only .csv and .xlsx files are supported." });

        // ── 1. Parse rows from file ───────────────────────────────────────
        List<RawImportRow> rawRows;
        try
        {
            rawRows = ext == ".xlsx"
                ? ParseXlsx(file)
                : ParseCsv(file);
        }
        catch (Exception ex)
        {
            return BadRequest(new { success = false, error = $"Could not parse file: {ex.Message}" });
        }

        if (rawRows.Count == 0)
            return BadRequest(new { success = false, error = "The file contains no data rows." });

        // ── 2. Collect all unique SKUs and validate against the DB ────────
        var allSkus = rawRows
            .SelectMany(r => new[] { r.BaseSku, r.CompatibleSku })
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Select(s => s!.Trim().ToUpper())
            .Distinct()
            .ToList();

        var existingSkus = (await _db.Products
            .Where(p => allSkus.Contains(p.Sku))
            .Select(p => p.Sku)
            .ToListAsync())
            .ToHashSet(StringComparer.Ordinal);

        // ── 3. Validate each row ──────────────────────────────────────────
        var validRows   = new List<ValidImportRow>();
        var errors      = new List<object>();
        var rowErrors   = new List<string>();

        for (int i = 0; i < rawRows.Count; i++)
        {
            var r        = rawRows[i];
            var rowNum   = i + 2; // 1-based + header row
            rowErrors.Clear();

            var baseSku   = r.BaseSku?.Trim().ToUpper()   ?? "";
            var compatSku = r.CompatibleSku?.Trim().ToUpper() ?? "";
            var typeRaw   = r.Type?.Trim() ?? "";
            var reason    = string.IsNullOrWhiteSpace(r.Reason) ? null : r.Reason.Trim();

            // Blank row guard
            if (string.IsNullOrWhiteSpace(baseSku) && string.IsNullOrWhiteSpace(compatSku) && string.IsNullOrWhiteSpace(typeRaw))
                continue;

            if (string.IsNullOrWhiteSpace(baseSku))
                rowErrors.Add("Base SKU is missing.");
            else if (!existingSkus.Contains(baseSku))
                rowErrors.Add($"Base SKU '{baseSku}' was not found in the product catalog.");

            if (string.IsNullOrWhiteSpace(compatSku))
                rowErrors.Add("Compatible SKU is missing.");
            else if (!existingSkus.Contains(compatSku))
                rowErrors.Add($"Compatible SKU '{compatSku}' was not found in the product catalog.");

            if (!string.IsNullOrWhiteSpace(baseSku) && !string.IsNullOrWhiteSpace(compatSku) &&
                string.Equals(baseSku, compatSku, StringComparison.OrdinalIgnoreCase))
                rowErrors.Add("Base SKU and Compatible SKU cannot be the same product.");

            var typeLower = typeRaw.ToLower();
            if (string.IsNullOrWhiteSpace(typeRaw))
                rowErrors.Add("Type is missing. It must be 'Whitelist' or 'Blacklist'.");
            else if (typeLower != "whitelist" && typeLower != "blacklist")
                rowErrors.Add($"Type '{typeRaw}' is invalid. It must be 'Whitelist' or 'Blacklist'.");

            if (rowErrors.Count > 0)
            {
                errors.Add(new
                {
                    row           = rowNum,
                    base_sku      = baseSku,
                    compatible_sku = compatSku,
                    type          = typeRaw,
                    messages      = rowErrors.ToList()
                });
                continue;
            }

            validRows.Add(new ValidImportRow(baseSku, compatSku, typeLower, reason, rowNum));
        }

        // ── 4. Insert valid rows, skipping duplicates ─────────────────────
        var imported = 0;
        var skipped  = new List<object>();
        var createdBy = CurrentUserEmail;

        foreach (var row in validRows)
        {
            var existing = await _db.CompatibilityOverrides
                .Where(o => (o.BaseSku == row.BaseSku && o.CompatibleSku == row.CompatibleSku) ||
                            (o.BaseSku == row.CompatibleSku && o.CompatibleSku == row.BaseSku))
                .Select(o => new { o.OverrideType })
                .FirstOrDefaultAsync();

            if (existing != null)
            {
                skipped.Add(new
                {
                    row           = row.RowNumber,
                    base_sku      = row.BaseSku,
                    compatible_sku = row.CompatibleSku,
                    reason        = existing.OverrideType == row.Type
                        ? $"A {row.Type} override for {row.BaseSku} ↔ {row.CompatibleSku} already exists."
                        : $"An override for {row.BaseSku} ↔ {row.CompatibleSku} already exists as '{existing.OverrideType}'. Delete it first."
                });
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

        return Ok(new
        {
            success  = errors.Count == 0,
            imported,
            skipped  = skipped.Count,
            skipped_details = skipped,
            error_count     = errors.Count,
            errors
        });
    }

    // ── Parsers ───────────────────────────────────────────────────────────

    private static List<RawImportRow> ParseXlsx(IFormFile file)
    {
        using var stream = file.OpenReadStream();
        using var wb     = new XLWorkbook(stream);
        var ws = wb.Worksheets.First();

        // Find header row (first non-empty row)
        var headerRow = ws.Row(1);
        var colMap    = MapColumns(
            Enumerable.Range(1, headerRow.LastCellUsed()?.Address.ColumnNumber ?? 10)
                      .Select(c => (c, headerRow.Cell(c).GetString().Trim()))
                      .ToList());

        var rows = new List<RawImportRow>();
        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;

        for (int r = 2; r <= lastRow; r++)
        {
            rows.Add(new RawImportRow(
                BaseSku:      colMap.TryGetValue("base sku",            out var b) ? ws.Row(r).Cell(b).GetString().Trim() : null,
                CompatibleSku: colMap.TryGetValue("compatible sku",      out var c) ? ws.Row(r).Cell(c).GetString().Trim() : null,
                Type:         colMap.TryGetValue("type",                out var t) ? ws.Row(r).Cell(t).GetString().Trim() : null,
                Reason:       colMap.TryGetValue("reason (optional)",   out var re) ? ws.Row(r).Cell(re).GetString().Trim()
                            : colMap.TryGetValue("reason",              out var r2) ? ws.Row(r).Cell(r2).GetString().Trim() : null
            ));
        }

        return rows;
    }

    private static List<RawImportRow> ParseCsv(IFormFile file)
    {
        using var reader = new StreamReader(file.OpenReadStream(), Encoding.UTF8);
        var lines = new List<string>();
        string? line;
        while ((line = reader.ReadLine()) != null)
            lines.Add(line);

        if (lines.Count == 0)
            throw new InvalidDataException("File is empty.");

        var headers = SplitCsvLine(lines[0]);
        var colMap  = MapColumns(headers.Select((h, i) => (i + 1, h.Trim())).ToList());

        var rows = new List<RawImportRow>();
        for (int i = 1; i < lines.Count; i++)
        {
            var cells = SplitCsvLine(lines[i]);
            string? Get(string key) => colMap.TryGetValue(key, out var idx) && idx <= cells.Count ? cells[idx - 1].Trim() : null;

            rows.Add(new RawImportRow(
                BaseSku:       Get("base sku"),
                CompatibleSku: Get("compatible sku"),
                Type:          Get("type"),
                Reason:        Get("reason (optional)") ?? Get("reason")
            ));
        }

        return rows;
    }

    /// <summary>Normalises column headers → 1-based column index map.</summary>
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

    /// <summary>RFC 4180-compliant CSV line splitter (handles quoted fields).</summary>
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
                else if (ch == '"')
                    inQuotes = false;
                else
                    current.Append(ch);
            }
            else
            {
                if (ch == '"')
                    inQuotes = true;
                else if (ch == ',')
                { fields.Add(current.ToString()); current.Clear(); }
                else
                    current.Append(ch);
            }
        }
        fields.Add(current.ToString());
        return fields;
    }

    // ── Supporting types ──────────────────────────────────────────────────

    private record RawImportRow(string? BaseSku, string? CompatibleSku, string? Type, string? Reason);
    private record ValidImportRow(string BaseSku, string CompatibleSku, string Type, string? Reason, int RowNumber);
}

public record CreateOverrideRequest(
    string? BaseSku,
    string? CompatibleSku,
    string? OverrideType,
    string? Reason
);
