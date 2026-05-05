using ORCA.Api.DTOs;
using Microsoft.AspNetCore.Http;

namespace ORCA.Api.Services.Interface;

public interface IOverrideService
{
    /// <summary>Returns all overrides, optionally filtered by SKU.</summary>
    Task<List<OverrideDto>> ListAsync(string? sku = null);

    /// <summary>
    /// Creates a new whitelist or blacklist override.
    /// Returns (success, errorMessage, created override or null).
    /// </summary>
    Task<OverrideCreateResult> CreateAsync(
        string baseSku, string compatibleSku, string overrideType, string? reason, string? createdBy);

    /// <summary>Deletes an override by ID. Returns (success, message/error).</summary>
    Task<OverrideDeleteResult> DeleteAsync(int id);

    /// <summary>
    /// Bulk-imports overrides from an uploaded XLSX or CSV file.
    /// Validates each row (SKU existence, type) and reports per-row errors.
    /// </summary>
    Task<OverrideImportResult> ImportAsync(IFormFile file, string? createdBy);

    /// <summary>Returns the bytes of a ready-to-fill CSV import template.</summary>
    byte[] GetImportTemplateCsv();
}

// ── Result types ──────────────────────────────────────────────────────────────

public record OverrideDto(
    int Id,
    string BaseSku,
    string? BaseProductName,
    string CompatibleSku,
    string? CompatibleProductName,
    string OverrideType,
    string? Reason,
    DateTime CreatedAt,
    string? CreatedBy
);

public record OverrideCreateResult(
    bool Success,
    string? Error,
    int StatusCode,             // HTTP status to return (200, 400, 409…)
    OverrideCreatedDto? Override = null
);

public record OverrideCreatedDto(
    int Id, string BaseSku, string CompatibleSku,
    string OverrideType, string? Reason, DateTime CreatedAt
);

public record OverrideDeleteResult(bool Success, string Message, int StatusCode);

public record OverrideImportResult(
    bool Success,
    int Imported,
    int Skipped,
    List<OverrideSkippedRow> SkippedDetails,
    int ErrorCount,
    List<OverrideErrorRow> Errors
);

public record OverrideSkippedRow(int Row, string BaseSku, string CompatibleSku, string Reason);

public record OverrideErrorRow(int Row, string BaseSku, string CompatibleSku, string Type, List<string> Messages);
