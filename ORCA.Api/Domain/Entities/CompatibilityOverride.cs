namespace ORCA.Api.Domain.Entities;

public class CompatibilityOverride
{
    public int Id { get; set; }
    public string BaseSku { get; set; } = string.Empty;
    public string CompatibleSku { get; set; } = string.Empty;
    public string OverrideType { get; set; } = string.Empty; // "whitelist" or "blacklist"
    public string? Reason { get; set; }
    public DateTime CreatedAt { get; set; }
}
