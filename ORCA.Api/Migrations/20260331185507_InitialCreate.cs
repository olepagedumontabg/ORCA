using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace ORCA.Api.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "compatibility_overrides",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    base_sku = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    compatible_sku = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    override_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    reason = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_compatibility_overrides", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "products",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    sku = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    product_name = table.Column<string>(type: "text", nullable: true),
                    brand = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    series = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    family = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    category = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    length = table.Column<decimal>(type: "numeric(10,2)", nullable: true),
                    width = table.Column<decimal>(type: "numeric(10,2)", nullable: true),
                    height = table.Column<decimal>(type: "numeric(10,2)", nullable: true),
                    nominal_dimensions = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    attributes = table.Column<string>(type: "jsonb", nullable: true),
                    product_page_url = table.Column<string>(type: "text", nullable: true),
                    image_url = table.Column<string>(type: "text", nullable: true),
                    ranking = table.Column<int>(type: "integer", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_products", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "sync_status",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    sync_type = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    started_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    completed_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    products_added = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    products_updated = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    products_deleted = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    compatibilities_updated = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    error_message = table.Column<string>(type: "text", nullable: true),
                    sync_metadata = table.Column<string>(type: "jsonb", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_sync_status", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "product_compatibility",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    base_product_id = table.Column<int>(type: "integer", nullable: false),
                    compatible_product_id = table.Column<int>(type: "integer", nullable: false),
                    match_reason = table.Column<string>(type: "text", nullable: true),
                    incompatibility_reason = table.Column<string>(type: "text", nullable: true),
                    computed_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_product_compatibility", x => x.id);
                    table.ForeignKey(
                        name: "FK_product_compatibility_products_base_product_id",
                        column: x => x.base_product_id,
                        principalTable: "products",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_product_compatibility_products_compatible_product_id",
                        column: x => x.compatible_product_id,
                        principalTable: "products",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_compatibility_overrides_base_sku",
                table: "compatibility_overrides",
                column: "base_sku");

            migrationBuilder.CreateIndex(
                name: "IX_compatibility_overrides_compatible_sku",
                table: "compatibility_overrides",
                column: "compatible_sku");

            migrationBuilder.CreateIndex(
                name: "uq_compatibility_override",
                table: "compatibility_overrides",
                columns: new[] { "base_sku", "compatible_sku", "override_type" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_compatibility_base",
                table: "product_compatibility",
                column: "base_product_id");

            migrationBuilder.CreateIndex(
                name: "idx_compatibility_compatible",
                table: "product_compatibility",
                column: "compatible_product_id");

            migrationBuilder.CreateIndex(
                name: "uq_product_compatibility",
                table: "product_compatibility",
                columns: new[] { "base_product_id", "compatible_product_id" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_products_brand",
                table: "products",
                column: "brand");

            migrationBuilder.CreateIndex(
                name: "IX_products_category",
                table: "products",
                column: "category");

            migrationBuilder.CreateIndex(
                name: "IX_products_family",
                table: "products",
                column: "family");

            migrationBuilder.CreateIndex(
                name: "IX_products_series",
                table: "products",
                column: "series");

            migrationBuilder.CreateIndex(
                name: "IX_products_sku",
                table: "products",
                column: "sku",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "idx_sync_status_started",
                table: "sync_status",
                column: "started_at");

            migrationBuilder.CreateIndex(
                name: "idx_sync_status_type",
                table: "sync_status",
                column: "sync_type");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "compatibility_overrides");

            migrationBuilder.DropTable(
                name: "product_compatibility");

            migrationBuilder.DropTable(
                name: "sync_status");

            migrationBuilder.DropTable(
                name: "products");
        }
    }
}
