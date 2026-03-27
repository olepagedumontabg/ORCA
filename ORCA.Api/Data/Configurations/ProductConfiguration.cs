using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using ORCA.Api.Domain.Entities;

namespace ORCA.Api.Data.Configurations;

public class ProductConfiguration : IEntityTypeConfiguration<Product>
{
    public void Configure(EntityTypeBuilder<Product> builder)
    {
        builder.ToTable("products");

        builder.HasKey(p => p.Id);
        builder.Property(p => p.Id).HasColumnName("id");

        builder.Property(p => p.Sku).HasColumnName("sku").HasMaxLength(50).IsRequired();
        builder.HasIndex(p => p.Sku).IsUnique();

        builder.Property(p => p.ProductName).HasColumnName("product_name");
        builder.Property(p => p.Brand).HasColumnName("brand").HasMaxLength(100);
        builder.HasIndex(p => p.Brand);

        builder.Property(p => p.Series).HasColumnName("series").HasMaxLength(100);
        builder.HasIndex(p => p.Series);

        builder.Property(p => p.Family).HasColumnName("family").HasMaxLength(100);
        builder.HasIndex(p => p.Family);

        builder.Property(p => p.Category).HasColumnName("category").HasMaxLength(50).IsRequired();
        builder.HasIndex(p => p.Category);

        builder.Property(p => p.Length).HasColumnName("length").HasColumnType("decimal(10,2)");
        builder.Property(p => p.Width).HasColumnName("width").HasColumnType("decimal(10,2)");
        builder.Property(p => p.Height).HasColumnName("height").HasColumnType("decimal(10,2)");
        builder.Property(p => p.NominalDimensions).HasColumnName("nominal_dimensions").HasMaxLength(50);

        builder.Property(p => p.Attributes).HasColumnName("attributes").HasColumnType("jsonb");

        builder.Property(p => p.ProductPageUrl).HasColumnName("product_page_url");
        builder.Property(p => p.ImageUrl).HasColumnName("image_url");

        builder.Property(p => p.Ranking).HasColumnName("ranking");

        builder.Property(p => p.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        builder.Property(p => p.UpdatedAt).HasColumnName("updated_at").HasDefaultValueSql("now()");
    }
}
