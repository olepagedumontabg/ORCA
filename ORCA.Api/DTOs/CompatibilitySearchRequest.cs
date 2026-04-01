namespace ORCA.Api.DTOs;

public class CompatibilitySearchRequest
{
    public string Sku { get; set; } = string.Empty;
    public string? Category { get; set; }
    public string? Brand { get; set; }
    public string? Serie { get; set; }
}
