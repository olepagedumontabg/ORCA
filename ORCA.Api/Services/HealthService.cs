using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Services;

public class HealthService : IHealthService
{
    private readonly OrcaDbContext _db;

    public HealthService(OrcaDbContext db)
    {
        _db = db;
    }

    public async Task<HealthResult> GetAsync()
    {
        try
        {
            var productCount       = await _db.Products.CountAsync();
            var compatibilityCount = await _db.ProductCompatibilities.CountAsync();

            return new HealthResult(
                Status:             "healthy",
                ProductCount:       productCount,
                CompatibilityCount: compatibilityCount,
                Timestamp:          DateTime.UtcNow
            );
        }
        catch (Exception ex)
        {
            return new HealthResult(
                Status:             "unhealthy",
                ProductCount:       0,
                CompatibilityCount: 0,
                Timestamp:          DateTime.UtcNow,
                Error:              ex.Message
            );
        }
    }
}
