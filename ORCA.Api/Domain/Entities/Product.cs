namespace ORCA.Api.Domain.Entities;

public class Product
{
    public int Id { get; set; }
    public string Sku { get; set; } = string.Empty;
    public string? ProductName { get; set; }
    public string? Brand { get; set; }
    public string? Series { get; set; }
    public string? Family { get; set; }
    public string Category { get; set; } = string.Empty;

    public decimal? Length { get; set; }
    public decimal? Width { get; set; }
    public decimal? Height { get; set; }
    public string? NominalDimensions { get; set; }

    public string? Attributes { get; set; } // JSON column

    public string? ProductPageUrl { get; set; }
    public string? ImageUrl { get; set; }

    public string? AlternateId1 { get; set; }
    public string? AlternateId2 { get; set; }
    public string? AlternateId3 { get; set; }

    public int? Ranking { get; set; }

    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }

    public ICollection<ProductCompatibility> CompatibilitiesFrom { get; set; } = new List<ProductCompatibility>();
    public ICollection<ProductCompatibility> CompatibilitiesTo { get; set; } = new List<ProductCompatibility>();
}
