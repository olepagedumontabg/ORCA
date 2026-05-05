using Microsoft.AspNetCore.Mvc;
using ORCA.Api.Services.Interface;
using System.Security.Claims;

namespace ORCA.Api.Controllers;

/// <summary>
/// Manages compatibility overrides.
/// All endpoints require Auth0 login and the ORCA - Editor (or Admin) role.
/// </summary>
[ApiController]
public class OverrideController : ControllerBase
{
    private readonly IOverrideService _overrides;

    public OverrideController(IOverrideService overrides)
    {
        _overrides = overrides;
    }

    private IActionResult? RequireEditor()
    {
        if (User?.Identity?.IsAuthenticated != true)
            return Unauthorized(new { success = false, error = "Authentication required." });

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
        var deny = RequireEditor();
        if (deny != null) return deny;

        var overrides = await _overrides.ListAsync(sku);
        return Ok(new { success = true, count = overrides.Count, overrides });
    }

    // ── POST /api/overrides ───────────────────────────────────────────────

    [HttpPost("api/overrides")]
    public async Task<IActionResult> Create([FromBody] CreateOverrideRequest request)
    {
        var deny = RequireEditor();
        if (deny != null) return deny;

        if (string.IsNullOrWhiteSpace(request.BaseSku))
            return BadRequest(new { success = false, error = "baseSku is required." });
        if (string.IsNullOrWhiteSpace(request.CompatibleSku))
            return BadRequest(new { success = false, error = "compatibleSku is required." });
        if (string.IsNullOrWhiteSpace(request.OverrideType))
            return BadRequest(new { success = false, error = "overrideType is required." });

        var result = await _overrides.CreateAsync(
            request.BaseSku, request.CompatibleSku, request.OverrideType,
            request.Reason, CurrentUserEmail);

        if (!result.Success)
            return StatusCode(result.StatusCode, new { success = false, error = result.Error });

        return Ok(new
        {
            success = true,
            message = $"{result.Override!.OverrideType} override created: {result.Override.BaseSku} ↔ {result.Override.CompatibleSku}",
            @override = result.Override
        });
    }

    // ── DELETE /api/overrides/{id} ────────────────────────────────────────

    [HttpDelete("api/overrides/{id:int}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deny = RequireEditor();
        if (deny != null) return deny;

        var result = await _overrides.DeleteAsync(id);

        return StatusCode(result.StatusCode,
            result.Success
                ? (object)new { success = true,  message = result.Message }
                : (object)new { success = false, error   = result.Message });
    }

    // ── GET /api/overrides/import-template ────────────────────────────────

    [HttpGet("api/overrides/import-template")]
    public IActionResult DownloadTemplate()
    {
        var deny = RequireEditor();
        if (deny != null) return deny;

        return File(_overrides.GetImportTemplateCsv(), "text/csv", "overrides-import-template.csv");
    }

    // ── POST /api/overrides/import ────────────────────────────────────────

    [HttpPost("api/overrides/import")]
    [RequestSizeLimit(10 * 1024 * 1024)]
    public async Task<IActionResult> Import(IFormFile? file)
    {
        var deny = RequireEditor();
        if (deny != null) return deny;

        if (file == null || file.Length == 0)
            return BadRequest(new { success = false, error = "No file uploaded." });

        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (ext != ".csv" && ext != ".xlsx")
            return BadRequest(new { success = false, error = "Only .csv and .xlsx files are supported." });

        var result = await _overrides.ImportAsync(file, CurrentUserEmail);

        return Ok(new
        {
            result.Success,
            result.Imported,
            result.Skipped,
            skipped_details = result.SkippedDetails,
            error_count     = result.ErrorCount,
            result.Errors
        });
    }
}

public record CreateOverrideRequest(
    string? BaseSku,
    string? CompatibleSku,
    string? OverrideType,
    string? Reason
);
