using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using System.Security.Claims;

namespace ORCA.Api.Controllers;

/// <summary>
/// Manages compatibility overrides. All endpoints require Auth0 login and the 'override-admin' role.
/// API endpoints return JSON 401/403 (not HTML redirects) so the browser-side JS receives clean errors.
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
    /// Checks authentication + role for API endpoints and returns a JSON error result when
    /// the check fails. Returns null when the caller is authorised to proceed.
    /// This replaces attribute-based auth because ASP.NET's default challenge handler
    /// issues an HTML redirect (302) rather than a JSON 401 for cookie-authenticated API routes.
    /// </summary>
    private IActionResult? RequireOverrideAdmin()
    {
        if (User?.Identity?.IsAuthenticated != true)
            return Unauthorized(new { success = false, error = "Authentication required. Please log in at /overrides." });

        if (!User.IsInRole("ORCA Admin"))
            return StatusCode(403, new { success = false, error = "The 'ORCA Admin' role is required to manage overrides." });

        return null;
    }

    /// <summary>
    /// GET /api/overrides
    /// List all compatibility overrides. Optionally filter by ?sku= to show only overrides for a given SKU.
    /// Requires: authenticated + override-admin role.
    /// </summary>
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

    /// <summary>
    /// POST /api/overrides
    /// Create a new whitelist or blacklist override.
    /// Body: { baseSku, compatibleSku, overrideType ("whitelist"|"blacklist"), reason? }
    /// Requires: authenticated + override-admin role.
    /// </summary>
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

        var baseSku = request.BaseSku.Trim().ToUpper();
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

        var createdBy = User.FindFirst(ClaimTypes.Email)?.Value
                     ?? User.FindFirst("email")?.Value
                     ?? User.Identity?.Name;

        var entry = new CompatibilityOverride
        {
            BaseSku = baseSku,
            CompatibleSku = compatSku,
            OverrideType = type,
            Reason = string.IsNullOrWhiteSpace(request.Reason) ? null : request.Reason.Trim(),
            CreatedAt = DateTime.UtcNow,
            CreatedBy = createdBy
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
    /// Requires: authenticated + override-admin role.
    /// </summary>
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
}

public record CreateOverrideRequest(
    string? BaseSku,
    string? CompatibleSku,
    string? OverrideType,
    string? Reason
);
