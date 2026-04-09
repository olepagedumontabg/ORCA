namespace ORCA.Api.Domain.Entities;

public class ProductCompatibility
{
    public int Id { get; set; }
    public int BaseProductId { get; set; }
    public int CompatibleProductId { get; set; }
    public string? Category { get; set; }
    public string? MatchReason { get; set; }
    public string? IncompatibilityReason { get; set; }

    public DateTime ComputedAt { get; set; }

    public Product BaseProduct { get; set; } = null!;
    public Product CompatibleProduct { get; set; } = null!;
}
