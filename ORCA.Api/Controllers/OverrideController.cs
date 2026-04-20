using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Controllers;

[ApiController]
public class OverrideController : ControllerBase
{
    private readonly OrcaDbContext _db;

    public OverrideController(OrcaDbContext db)
    {
        _db = db;
    }

    /// <summary>
    /// GET /api/overrides
    /// List all compatibility overrides. Optionally filter by ?sku= to show only overrides for a given SKU.
    /// </summary>
    [HttpGet("api/overrides")]
    public async Task<IActionResult> List([FromQuery] string? sku = null)
    {
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
                o.CompatibleSku,
                o.OverrideType,
                o.Reason,
                o.CreatedAt
            })
            .ToListAsync();

        return Ok(new { success = true, count = overrides.Count, overrides });
    }

    /// <summary>
    /// POST /api/overrides
    /// Create a new whitelist or blacklist override.
    /// Body: { baseSku, compatibleSku, overrideType ("whitelist"|"blacklist"), reason? }
    /// </summary>
    [HttpPost("api/overrides")]
    public async Task<IActionResult> Create([FromBody] CreateOverrideRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.BaseSku))
            return BadRequest(new { success = false, error = "baseSku is required" });
        if (string.IsNullOrWhiteSpace(request.CompatibleSku))
            return BadRequest(new { success = false, error = "compatibleSku is required" });

        var type = request.OverrideType?.Trim().ToLower();
        if (type != "whitelist" && type != "blacklist")
            return BadRequest(new { success = false, error = "overrideType must be 'whitelist' or 'blacklist'" });

        var baseSku = request.BaseSku.Trim().ToUpper();
        var compatSku = request.CompatibleSku.Trim().ToUpper();

        if (string.Equals(baseSku, compatSku, StringComparison.OrdinalIgnoreCase))
            return BadRequest(new { success = false, error = "baseSku and compatibleSku cannot be the same product" });

        // Verify both products exist
        var baseExists = await _db.Products.AnyAsync(p => p.Sku == baseSku);
        if (!baseExists)
            return BadRequest(new { success = false, error = $"Product not found: {baseSku}" });

        var compatExists = await _db.Products.AnyAsync(p => p.Sku == compatSku);
        if (!compatExists)
            return BadRequest(new { success = false, error = $"Product not found: {compatSku}" });

        // Check for duplicate
        var duplicate = await _db.CompatibilityOverrides.AnyAsync(o =>
            o.BaseSku == baseSku &&
            o.CompatibleSku == compatSku &&
            o.OverrideType == type);

        if (duplicate)
            return Conflict(new { success = false, error = $"A {type} override for {baseSku} ↔ {compatSku} already exists" });

        var entry = new CompatibilityOverride
        {
            BaseSku = baseSku,
            CompatibleSku = compatSku,
            OverrideType = type,
            Reason = string.IsNullOrWhiteSpace(request.Reason) ? null : request.Reason.Trim(),
            CreatedAt = DateTime.UtcNow
        };

        _db.CompatibilityOverrides.Add(entry);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            success = true,
            message = $"{type} override created: {baseSku} ↔ {compatSku}",
            @override = new
            {
                entry.Id,
                entry.BaseSku,
                entry.CompatibleSku,
                entry.OverrideType,
                entry.Reason,
                entry.CreatedAt
            }
        });
    }

    /// <summary>
    /// DELETE /api/overrides/{id}
    /// Remove an override by its database ID.
    /// </summary>
    [HttpDelete("api/overrides/{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
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
}

public record CreateOverrideRequest(
    string? BaseSku,
    string? CompatibleSku,
    string? OverrideType,
    string? Reason
);
