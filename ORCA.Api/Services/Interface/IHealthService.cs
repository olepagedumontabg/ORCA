namespace ORCA.Api.Services.Interface;

public interface IHealthService
{
    Task<HealthResult> GetAsync();
}

public record HealthResult(
    string Status,
    int ProductCount,
    int CompatibilityCount,
    DateTime Timestamp,
    string? Error = null
);
