namespace ORCA.Api.DTOs;

public class CompatibilityCategoryResult
{
    public string Category { get; set; } = string.Empty;
    public List<CompatibleProductDto> Products { get; set; } = new();

    /// <summary>
    /// If set, indicates why this category has no compatible products.
    /// </summary>
    public string? IncompatibilityReason { get; set; }
}
