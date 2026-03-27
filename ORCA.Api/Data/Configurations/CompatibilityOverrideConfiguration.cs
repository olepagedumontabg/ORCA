using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data.Configurations;

public class CompatibilityOverrideConfiguration : IEntityTypeConfiguration<CompatibilityOverride>
{
    public void Configure(EntityTypeBuilder<CompatibilityOverride> builder)
    {
        builder.ToTable("compatibility_overrides");

        builder.HasKey(co => co.Id);
        builder.Property(co => co.Id).HasColumnName("id");

        builder.Property(co => co.BaseSku).HasColumnName("base_sku").HasMaxLength(50).IsRequired();
        builder.HasIndex(co => co.BaseSku);

        builder.Property(co => co.CompatibleSku).HasColumnName("compatible_sku").HasMaxLength(50).IsRequired();
        builder.HasIndex(co => co.CompatibleSku);

        builder.Property(co => co.OverrideType).HasColumnName("override_type").HasMaxLength(20).IsRequired();
        builder.Property(co => co.Reason).HasColumnName("reason");
        builder.Property(co => co.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");

        builder.HasIndex(co => new { co.BaseSku, co.CompatibleSku, co.OverrideType })
            .IsUnique()
            .HasDatabaseName("uq_compatibility_override");
    }
}
