namespace ORCA.Api.Domain.Entities;

public class SyncStatus
{
    public int Id { get; set; }
    public string SyncType { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public DateTime StartedAt { get; set; }
    public DateTime? CompletedAt { get; set; }

    public int ProductsAdded { get; set; }
    public int ProductsUpdated { get; set; }
    public int ProductsDeleted { get; set; }
    public int CompatibilitiesUpdated { get; set; }

    public string? ErrorMessage { get; set; }
    public string? SyncMetadata { get; set; } // JSON column
}
