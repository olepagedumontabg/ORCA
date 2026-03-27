using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data.Configurations;

public class SyncStatusConfiguration : IEntityTypeConfiguration<SyncStatus>
{
    public void Configure(EntityTypeBuilder<SyncStatus> builder)
    {
        builder.ToTable("sync_status");

        builder.HasKey(s => s.Id);
        builder.Property(s => s.Id).HasColumnName("id");

        builder.Property(s => s.SyncType).HasColumnName("sync_type").HasMaxLength(50).IsRequired();
        builder.HasIndex(s => s.SyncType).HasDatabaseName("idx_sync_status_type");

        builder.Property(s => s.Status).HasColumnName("status").HasMaxLength(20).IsRequired();

        builder.Property(s => s.StartedAt).HasColumnName("started_at").IsRequired().HasDefaultValueSql("now()");
        builder.HasIndex(s => s.StartedAt).HasDatabaseName("idx_sync_status_started");

        builder.Property(s => s.CompletedAt).HasColumnName("completed_at");

        builder.Property(s => s.ProductsAdded).HasColumnName("products_added").HasDefaultValue(0);
        builder.Property(s => s.ProductsUpdated).HasColumnName("products_updated").HasDefaultValue(0);
        builder.Property(s => s.ProductsDeleted).HasColumnName("products_deleted").HasDefaultValue(0);
        builder.Property(s => s.CompatibilitiesUpdated).HasColumnName("compatibilities_updated").HasDefaultValue(0);

        builder.Property(s => s.ErrorMessage).HasColumnName("error_message");
        builder.Property(s => s.SyncMetadata).HasColumnName("sync_metadata").HasColumnType("jsonb");
    }
}
