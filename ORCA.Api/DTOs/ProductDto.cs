namespace ORCA.Api.DTOs;

public class ProductDto
{
    public int Id { get; set; }
    public string Sku { get; set; } = string.Empty;
    public string? Name { get; set; }
    public string? Brand { get; set; }
    public string? Series { get; set; }
    public string? Family { get; set; }
    public string Category { get; set; } = string.Empty;
    public string? ImageUrl { get; set; }
    public string? ProductPageUrl { get; set; }
    public string? NominalDimensions { get; set; }
    public string? AlternateId1 { get; set; }
    public string? AlternateId2 { get; set; }
    public string? AlternateId3 { get; set; }
    public string? ParentId { get; set; }
}
