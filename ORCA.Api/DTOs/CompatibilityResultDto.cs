namespace ORCA.Api.DTOs;

public class CompatibilityResultDto
{
    public bool Success { get; set; }
    public ProductDto? Product { get; set; }
    public List<CompatibilityCategoryResult> Compatibles { get; set; } = new();
    public Dictionary<string, string> IncompatibilityReasons { get; set; } = new();
    public int TotalCategories { get; set; }
    public string DataSource { get; set; } = "database";
    public string? ErrorMessage { get; set; }
}
