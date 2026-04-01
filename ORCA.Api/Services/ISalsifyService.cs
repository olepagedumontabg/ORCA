namespace ORCA.Api.Services;

public interface ISalsifyService
{
    Task<SalsifyWebhookResult> ProcessWebhookAsync(string productFeedUrl, string? channelId, string? channelName);
    Task<List<SyncStatusDto>> GetStatusAsync(int? syncId, int limit);
    Task<CleanupResult> CleanupAsync(int olderThanDays);
}

public record SalsifyWebhookResult(bool Success, string Message, int? SyncId, string? Error = null);
public record CleanupResult(bool Success, int DeletedCount, string Message);

public record SyncStatusDto(
    int Id,
    string SyncType,
    string Status,
    DateTime StartedAt,
    DateTime? CompletedAt,
    int ProductsAdded,
    int ProductsUpdated,
    int ProductsDeleted,
    int CompatibilitiesUpdated,
    string? ErrorMessage,
    object? Metadata
);
