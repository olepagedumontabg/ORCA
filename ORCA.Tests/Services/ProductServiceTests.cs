using Microsoft.EntityFrameworkCore;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services;

namespace ORCA.Tests.Services;

[TestClass]
public class ProductServiceTests
{
    // ─── helpers ──────────────────────────────────────────────────────────────

    private static OrcaDbContext CreateContext(string dbName)
    {
        var options = new DbContextOptionsBuilder<OrcaDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;
        return new OrcaDbContext(options);
    }

    private static Product MakeProduct(int id, string sku, string category,
        string? brand = null, string? name = null, string? series = null,
        string? family = null, string? imageUrl = null, string? pageUrl = null,
        string? nominalDimensions = null) => new()
    {
        Id = id,
        Sku = sku,
        Category = category,
        Brand = brand,
        ProductName = name,
        Series = series,
        Family = family,
        ImageUrl = imageUrl,
        ProductPageUrl = pageUrl,
        NominalDimensions = nominalDimensions,
        CreatedAt = DateTime.UtcNow,
        UpdatedAt = DateTime.UtcNow
    };

    // ─── GetBySkuAsync ─────────────────────────────────────────────────────────

    [TestMethod]
    public async Task GetBySkuAsync_ExistingSku_ReturnsProduct()
    {
        await using var ctx = CreateContext(nameof(GetBySkuAsync_ExistingSku_ReturnsProduct));
        ctx.Products.Add(MakeProduct(1, "SB-100", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetBySkuAsync("SB-100");

        Assert.IsNotNull(result);
        Assert.AreEqual("SB-100", result.Sku);
    }

    [TestMethod]
    public async Task GetBySkuAsync_LowercaseInput_NormalisesToUpperAndFindsProduct()
    {
        await using var ctx = CreateContext(nameof(GetBySkuAsync_LowercaseInput_NormalisesToUpperAndFindsProduct));
        ctx.Products.Add(MakeProduct(1, "SB-100", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetBySkuAsync("sb-100");

        Assert.IsNotNull(result);
        Assert.AreEqual("SB-100", result.Sku);
    }

    [TestMethod]
    public async Task GetBySkuAsync_MixedCaseInput_NormalisesToUpperAndFindsProduct()
    {
        await using var ctx = CreateContext(nameof(GetBySkuAsync_MixedCaseInput_NormalisesToUpperAndFindsProduct));
        ctx.Products.Add(MakeProduct(1, "SB-100", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetBySkuAsync("Sb-100");

        Assert.IsNotNull(result);
        Assert.AreEqual("SB-100", result.Sku);
    }

    [TestMethod]
    public async Task GetBySkuAsync_NonExistentSku_ReturnsNull()
    {
        await using var ctx = CreateContext(nameof(GetBySkuAsync_NonExistentSku_ReturnsNull));
        ctx.Products.Add(MakeProduct(1, "SB-100", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetBySkuAsync("DOES-NOT-EXIST");

        Assert.IsNull(result);
    }

    [TestMethod]
    public async Task GetBySkuAsync_EmptyDatabase_ReturnsNull()
    {
        await using var ctx = CreateContext(nameof(GetBySkuAsync_EmptyDatabase_ReturnsNull));

        var svc = new ProductService(ctx);
        var result = await svc.GetBySkuAsync("SB-100");

        Assert.IsNull(result);
    }

    // ─── GetByIdAsync ──────────────────────────────────────────────────────────

    [TestMethod]
    public async Task GetByIdAsync_ExistingId_ReturnsProduct()
    {
        await using var ctx = CreateContext(nameof(GetByIdAsync_ExistingId_ReturnsProduct));
        ctx.Products.Add(MakeProduct(42, "SB-200", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetByIdAsync(42);

        Assert.IsNotNull(result);
        Assert.AreEqual(42, result.Id);
        Assert.AreEqual("SB-200", result.Sku);
    }

    [TestMethod]
    public async Task GetByIdAsync_NonExistentId_ReturnsNull()
    {
        await using var ctx = CreateContext(nameof(GetByIdAsync_NonExistentId_ReturnsNull));
        ctx.Products.Add(MakeProduct(1, "SB-100", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var result = await svc.GetByIdAsync(999);

        Assert.IsNull(result);
    }

    [TestMethod]
    public async Task GetByIdAsync_EmptyDatabase_ReturnsNull()
    {
        await using var ctx = CreateContext(nameof(GetByIdAsync_EmptyDatabase_ReturnsNull));

        var svc = new ProductService(ctx);
        var result = await svc.GetByIdAsync(1);

        Assert.IsNull(result);
    }

    // ─── GetAllAsync — no filter ───────────────────────────────────────────────

    [TestMethod]
    public async Task GetAllAsync_NoFilter_ReturnsAllProductsAndCorrectCount()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_NoFilter_ReturnsAllProductsAndCorrectCount));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "BB-002", "Bathtub"),
            MakeProduct(3, "CC-003", "Shower Door"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync();

        Assert.AreEqual(3, totalCount);
        Assert.AreEqual(3, products.Count);
    }

    [TestMethod]
    public async Task GetAllAsync_EmptyDatabase_ReturnsEmptyListAndZeroCount()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_EmptyDatabase_ReturnsEmptyListAndZeroCount));

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync();

        Assert.AreEqual(0, totalCount);
        Assert.AreEqual(0, products.Count);
    }

    [TestMethod]
    public async Task GetAllAsync_ResultsOrderedBySku()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_ResultsOrderedBySku));
        ctx.Products.AddRange(
            MakeProduct(1, "CC-003", "Shower Door"),
            MakeProduct(2, "AA-001", "Shower Base"),
            MakeProduct(3, "BB-002", "Bathtub"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, _) = await svc.GetAllAsync();

        Assert.AreEqual("AA-001", products[0].Sku);
        Assert.AreEqual("BB-002", products[1].Sku);
        Assert.AreEqual("CC-003", products[2].Sku);
    }

    [TestMethod]
    public async Task GetAllAsync_MapsAllDtoFieldsCorrectly()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_MapsAllDtoFieldsCorrectly));
        ctx.Products.Add(MakeProduct(5, "SB-500", "Shower Base",
            brand: "MAAX", name: "Tile Redi", series: "Redi Trench",
            family: "Redi", imageUrl: "https://img.test/img.jpg",
            pageUrl: "https://products.test/sb500", nominalDimensions: "36 x 60"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, _) = await svc.GetAllAsync();
        var dto = products.Single();

        Assert.AreEqual(5, dto.Id);
        Assert.AreEqual("SB-500", dto.Sku);
        Assert.AreEqual("Tile Redi", dto.Name);
        Assert.AreEqual("MAAX", dto.Brand);
        Assert.AreEqual("Redi Trench", dto.Series);
        Assert.AreEqual("Redi", dto.Family);
        Assert.AreEqual("Shower Base", dto.Category);
        Assert.AreEqual("https://img.test/img.jpg", dto.ImageUrl);
        Assert.AreEqual("https://products.test/sb500", dto.ProductPageUrl);
        Assert.AreEqual("36 x 60", dto.NominalDimensions);
    }

    // ─── GetAllAsync — category filter ────────────────────────────────────────

    [TestMethod]
    public async Task GetAllAsync_WithCategoryFilter_ReturnsOnlyMatchingProducts()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_WithCategoryFilter_ReturnsOnlyMatchingProducts));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "BB-002", "Bathtub"),
            MakeProduct(3, "CC-003", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(category: "Shower Base");

        Assert.AreEqual(2, totalCount);
        Assert.IsTrue(products.All(p => p.Category == "Shower Base"));
    }

    [TestMethod]
    public async Task GetAllAsync_WithCategoryFilter_NoMatches_ReturnsEmptyAndZeroCount()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_WithCategoryFilter_NoMatches_ReturnsEmptyAndZeroCount));
        ctx.Products.Add(MakeProduct(1, "AA-001", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(category: "Bathtub");

        Assert.AreEqual(0, totalCount);
        Assert.AreEqual(0, products.Count);
    }

    [TestMethod]
    public async Task GetAllAsync_WhitespaceOnlyCategory_TreatedAsNoFilter()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_WhitespaceOnlyCategory_TreatedAsNoFilter));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "BB-002", "Bathtub"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(category: "   ");

        Assert.AreEqual(2, totalCount);
        Assert.AreEqual(2, products.Count);
    }

    // ─── GetAllAsync — pagination ──────────────────────────────────────────────

    [TestMethod]
    public async Task GetAllAsync_FirstPage_ReturnsCorrectSlice()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_FirstPage_ReturnsCorrectSlice));
        for (int i = 1; i <= 10; i++)
            ctx.Products.Add(MakeProduct(i, $"SKU-{i:D3}", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(page: 1, pageSize: 3);

        Assert.AreEqual(10, totalCount);
        Assert.AreEqual(3, products.Count);
    }

    [TestMethod]
    public async Task GetAllAsync_SecondPage_ReturnsNextSlice()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_SecondPage_ReturnsNextSlice));
        for (int i = 1; i <= 10; i++)
            ctx.Products.Add(MakeProduct(i, $"SKU-{i:D3}", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (page1, _) = await svc.GetAllAsync(page: 1, pageSize: 3);
        var (page2, _) = await svc.GetAllAsync(page: 2, pageSize: 3);

        // No overlap between pages
        var page1Skus = page1.Select(p => p.Sku).ToHashSet();
        Assert.IsFalse(page2.Any(p => page1Skus.Contains(p.Sku)));
    }

    [TestMethod]
    public async Task GetAllAsync_PageBeyondData_ReturnsEmptyList()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_PageBeyondData_ReturnsEmptyList));
        ctx.Products.Add(MakeProduct(1, "SKU-001", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(page: 99, pageSize: 10);

        Assert.AreEqual(1, totalCount);
        Assert.AreEqual(0, products.Count);
    }

    [TestMethod]
    public async Task GetAllAsync_LastPagePartialFill_ReturnsRemainder()
    {
        await using var ctx = CreateContext(nameof(GetAllAsync_LastPagePartialFill_ReturnsRemainder));
        for (int i = 1; i <= 7; i++)
            ctx.Products.Add(MakeProduct(i, $"SKU-{i:D3}", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var (products, totalCount) = await svc.GetAllAsync(page: 2, pageSize: 5);

        Assert.AreEqual(7, totalCount);
        Assert.AreEqual(2, products.Count);
    }

    // ─── GetCategoriesAsync ────────────────────────────────────────────────────

    [TestMethod]
    public async Task GetCategoriesAsync_ReturnsCategoriesWithCorrectCounts()
    {
        await using var ctx = CreateContext(nameof(GetCategoriesAsync_ReturnsCategoriesWithCorrectCounts));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "AA-002", "Shower Base"),
            MakeProduct(3, "BB-001", "Bathtub"),
            MakeProduct(4, "CC-001", "Shower Door"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var categories = await svc.GetCategoriesAsync();

        Assert.AreEqual(3, categories.Count);

        var showerBase = categories.Single(c => c.Category == "Shower Base");
        var bathtub = categories.Single(c => c.Category == "Bathtub");
        var showerDoor = categories.Single(c => c.Category == "Shower Door");

        Assert.AreEqual(2, showerBase.Count);
        Assert.AreEqual(1, bathtub.Count);
        Assert.AreEqual(1, showerDoor.Count);
    }

    [TestMethod]
    public async Task GetCategoriesAsync_ResultsOrderedAlphabetically()
    {
        await using var ctx = CreateContext(nameof(GetCategoriesAsync_ResultsOrderedAlphabetically));
        ctx.Products.AddRange(
            MakeProduct(1, "CC-001", "Shower Door"),
            MakeProduct(2, "AA-001", "Bathtub"),
            MakeProduct(3, "BB-001", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var categories = await svc.GetCategoriesAsync();

        Assert.AreEqual("Bathtub", categories[0].Category);
        Assert.AreEqual("Shower Base", categories[1].Category);
        Assert.AreEqual("Shower Door", categories[2].Category);
    }

    [TestMethod]
    public async Task GetCategoriesAsync_EmptyDatabase_ReturnsEmptyList()
    {
        await using var ctx = CreateContext(nameof(GetCategoriesAsync_EmptyDatabase_ReturnsEmptyList));

        var svc = new ProductService(ctx);
        var categories = await svc.GetCategoriesAsync();

        Assert.AreEqual(0, categories.Count);
    }

    [TestMethod]
    public async Task GetCategoriesAsync_SingleCategory_ReturnsOneEntry()
    {
        await using var ctx = CreateContext(nameof(GetCategoriesAsync_SingleCategory_ReturnsOneEntry));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "AA-002", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var categories = await svc.GetCategoriesAsync();

        Assert.AreEqual(1, categories.Count);
        Assert.AreEqual("Shower Base", categories[0].Category);
        Assert.AreEqual(2, categories[0].Count);
    }

    // ─── GetProductsByCategoriesAsync ──────────────────────────────────────────

    [TestMethod]
    public async Task GetProductsByCategoriesAsync_MatchingCategories_ReturnsCorrectProducts()
    {
        await using var ctx = CreateContext(nameof(GetProductsByCategoriesAsync_MatchingCategories_ReturnsCorrectProducts));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "BB-001", "Bathtub"),
            MakeProduct(3, "CC-001", "Shower Door"),
            MakeProduct(4, "DD-001", "Shower Wall"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var results = await svc.GetProductsByCategoriesAsync(["Shower Base", "Bathtub"]);

        Assert.AreEqual(2, results.Count);
        Assert.IsTrue(results.Any(p => p.Sku == "AA-001"));
        Assert.IsTrue(results.Any(p => p.Sku == "BB-001"));
    }

    [TestMethod]
    public async Task GetProductsByCategoriesAsync_NoMatchingCategory_ReturnsEmpty()
    {
        await using var ctx = CreateContext(nameof(GetProductsByCategoriesAsync_NoMatchingCategory_ReturnsEmpty));
        ctx.Products.Add(MakeProduct(1, "AA-001", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var results = await svc.GetProductsByCategoriesAsync(["Bathtub"]);

        Assert.AreEqual(0, results.Count);
    }

    [TestMethod]
    public async Task GetProductsByCategoriesAsync_EmptyList_ReturnsEmpty()
    {
        await using var ctx = CreateContext(nameof(GetProductsByCategoriesAsync_EmptyList_ReturnsEmpty));
        ctx.Products.Add(MakeProduct(1, "AA-001", "Shower Base"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var results = await svc.GetProductsByCategoriesAsync([]);

        Assert.AreEqual(0, results.Count);
    }

    [TestMethod]
    public async Task GetProductsByCategoriesAsync_SingleCategory_ReturnsAllInCategory()
    {
        await using var ctx = CreateContext(nameof(GetProductsByCategoriesAsync_SingleCategory_ReturnsAllInCategory));
        ctx.Products.AddRange(
            MakeProduct(1, "SB-001", "Shower Base"),
            MakeProduct(2, "SB-002", "Shower Base"),
            MakeProduct(3, "BD-001", "Bathtub"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var results = await svc.GetProductsByCategoriesAsync(["Shower Base"]);

        Assert.AreEqual(2, results.Count);
        Assert.IsTrue(results.All(p => p.Category == "Shower Base"));
    }

    [TestMethod]
    public async Task GetProductsByCategoriesAsync_AllCategories_ReturnsAllProducts()
    {
        await using var ctx = CreateContext(nameof(GetProductsByCategoriesAsync_AllCategories_ReturnsAllProducts));
        ctx.Products.AddRange(
            MakeProduct(1, "AA-001", "Shower Base"),
            MakeProduct(2, "BB-001", "Bathtub"),
            MakeProduct(3, "CC-001", "Shower Door"));
        await ctx.SaveChangesAsync();

        var svc = new ProductService(ctx);
        var results = await svc.GetProductsByCategoriesAsync(["Shower Base", "Bathtub", "Shower Door"]);

        Assert.AreEqual(3, results.Count);
    }
}
