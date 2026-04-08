using Microsoft.EntityFrameworkCore;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data;

public class OrcaDbContext : DbContext
{
    public OrcaDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<OrcaDbContext>();

        optionsBuilder.UseNpgsql("Host=ep-spring-band-adsvk8mb-pooler.c-2.us-east-1.aws.neon.tech; Database=neondb; Username=neondb_owner; Password=npg_lVa3QMcFq2xk; SSL Mode=VerifyFull; Channel Binding=Require;");

        return new OrcaDbContext(optionsBuilder.Options);
    }
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
