using Microsoft.EntityFrameworkCore;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data;

public class OrcaDbContext : DbContext
{
    public OrcaDbContext(DbContextOptions<OrcaDbContext> options) : base(options) { }

    public DbSet<Product> Products => Set<Product>();
    public DbSet<ProductCompatibility> ProductCompatibilities => Set<ProductCompatibility>();
    public DbSet<CompatibilityOverride> CompatibilityOverrides => Set<CompatibilityOverride>();
    public DbSet<SyncStatus> SyncStatuses => Set<SyncStatus>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(OrcaDbContext).Assembly);
    }
}
