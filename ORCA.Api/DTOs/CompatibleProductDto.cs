namespace ORCA.Api.DTOs;

public class CompatibleProductDto
{
    public string Sku { get; set; } = string.Empty;
    public string? Name { get; set; }
    public string? Brand { get; set; }
    public string? Series { get; set; }
    public string? Family { get; set; }
    public string Category { get; set; } = string.Empty;
    public string? ImageUrl { get; set; }
    public string? ProductPageUrl { get; set; }
    public int? CompatibilityScore { get; set; }
    public string? MatchReason { get; set; }
    public bool IsCombo { get; set; }

    // For combo products (corner door + return panel)
    public CompatibleProductDto? SecondaryProduct { get; set; }
}
