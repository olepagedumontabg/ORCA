using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data.Configurations;

public class ProductCompatibilityConfiguration : IEntityTypeConfiguration<ProductCompatibility>
{
    public void Configure(EntityTypeBuilder<ProductCompatibility> builder)
    {
        builder.ToTable("product_compatibility");

        builder.HasKey(pc => pc.Id);
        builder.Property(pc => pc.Id).HasColumnName("id");

        builder.Property(pc => pc.BaseProductId).HasColumnName("base_product_id").IsRequired();
        builder.Property(pc => pc.CompatibleProductId).HasColumnName("compatible_product_id").IsRequired();

        builder.Property(pc => pc.MatchReason).HasColumnName("match_reason");
        builder.Property(pc => pc.IncompatibilityReason).HasColumnName("incompatibility_reason");
        builder.Property(pc => pc.ComputedAt).HasColumnName("computed_at").HasDefaultValueSql("now()");

        builder.HasIndex(pc => pc.BaseProductId).HasDatabaseName("idx_compatibility_base");
        builder.HasIndex(pc => pc.CompatibleProductId).HasDatabaseName("idx_compatibility_compatible");

        // Unique constraint
        builder.HasIndex(pc => new { pc.BaseProductId, pc.CompatibleProductId })
            .IsUnique()
            .HasDatabaseName("uq_product_compatibility");

        // Relationships
        builder.HasOne(pc => pc.BaseProduct)
            .WithMany(p => p.CompatibilitiesFrom)
            .HasForeignKey(pc => pc.BaseProductId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasOne(pc => pc.CompatibleProduct)
            .WithMany(p => p.CompatibilitiesTo)
            .HasForeignKey(pc => pc.CompatibleProductId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
