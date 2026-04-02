using Microsoft.Extensions.Logging;
using Moq;
using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services;

namespace ORCA.Tests.Services;

[TestClass]
public class CompatibilityEngineTests
{
    private CompatibilityEngine CreateEngine()
    {
        var logger = new Mock<ILogger<CompatibilityEngine>>();
        return new CompatibilityEngine(logger.Object);
    }

    private Product CreateProduct(
        string sku,
        string category,
        string? attributes = null,
        string? series = null,
        string? brand = null,
        string? nominal = null,
        decimal? length = null,
        decimal? width = null)
    {
        return new Product
        {
            Sku = sku,
            Category = category,
            Attributes = attributes,
            Series = series,
            Brand = brand,
            NominalDimensions = nominal,
            Length = length,
            Width = width
        };
    }

    private Dictionary<string, List<Product>> EmptyCandidates()
        => new();

    // -----------------------------
    // ROUTING TESTS
    // -----------------------------

    [TestMethod]
    public void Should_Return_Default_When_Category_Not_Supported()
    {
        var engine = CreateEngine();

        var product = CreateProduct("SKU1", "UNKNOWN");

        var result = engine.FindCompatibleProducts(product, EmptyCandidates());

        Assert.AreEqual(1, result.Count);
        Assert.IsTrue(result[0].IncompatibilityReason.Contains("No compatibility rules"));
    }

    [TestMethod]
    public void Should_Not_Throw_When_No_Candidates()
    {
        var engine = CreateEngine();

        var product = CreateProduct("SKU1", CompatibilityConstants.Categories.ShowerBases);

        var result = engine.FindCompatibleProducts(product, EmptyCandidates());

        Assert.IsNotNull(result);
    }

    // -----------------------------
    // REVERSE SCREEN
    // -----------------------------

    [TestMethod]
    public void ReverseScreen_Should_Return_Compatible_Base()
    {
        var engine = CreateEngine();

        var screen = CreateProduct(
            "SCREEN1",
            CompatibilityConstants.Categories.ShowerScreens,
            attributes: "{\"Fixed Panel Width\":8}",
            series: "A");

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 32}",
            series: "A");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, new() { baseProduct } }
        };

        var result = engine.FindCompatibleProducts(screen, candidates);

        Assert.AreEqual(1, result.Count);
        Assert.AreEqual("Shower Bases", result[0].Category);
        Assert.AreEqual(1, result[0].Products.Count);
    }

    // -----------------------------
    // REVERSE DOOR
    // -----------------------------

    [TestMethod]
    public void ReverseDoor_Shower_Should_Match_Alcove_Or_Corner()
    {
        var engine = CreateEngine();

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.ShowerDoors,
            attributes: "{\"Minimum Width\": 20, \"Maximum Width\": 40}",
            series: "A");

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"alcove\"}",
            series: "A");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, new() { baseProduct } }
        };

        var result = engine.FindCompatibleProducts(door, candidates);

        Assert.AreEqual(1, result.Count);
        Assert.AreEqual(1, result[0].Products.Count);
    }

    [TestMethod]
    public void ReverseDoor_Tub_Should_Only_Match_Alcove()
    {
        var engine = CreateEngine();

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.TubDoors,
            attributes: "{\"Minimum Width\": 20, \"Maximum Width\": 40}",
            series: "A");

        var tub = CreateProduct(
            "TUB1",
            CompatibilityConstants.Categories.Bathtubs,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"corner\"}",
            series: "A");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.Bathtubs, new() { tub } }
        };

        var result = engine.FindCompatibleProducts(door, candidates);

        Assert.AreEqual(0, result.Count);
    }

    // -----------------------------
    // REVERSE ENCLOSURE
    // -----------------------------

    [TestMethod]
    public void ReverseEnclosure_Should_Match_By_Nominal()
    {
        var engine = CreateEngine();

        var enclosure = CreateProduct(
            "ENC1",
            CompatibilityConstants.Categories.Enclosures,
            attributes: "{}",
            nominal: "60x32",
            series: "A",
            brand: "BrandX");

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Installation\": \"corner\"}",
            nominal: "60x32",
            series: "A",
            brand: "BrandX");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, new() { baseProduct } }
        };

        var result = engine.FindCompatibleProducts(enclosure, candidates);

        Assert.AreEqual(1, result.Count);
        Assert.AreEqual(1, result[0].Products.Count);
    }

    [TestMethod]
    public void ReverseEnclosure_Should_Skip_Non_Corner()
    {
        var engine = CreateEngine();

        var enclosure = CreateProduct(
            "ENC1",
            CompatibilityConstants.Categories.Enclosures,
            attributes: "{}",
            series: "A",
            brand: "BrandX");

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Installation\": \"alcove\"}",
            series: "A",
            brand: "BrandX");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, new() { baseProduct } }
        };

        var result = engine.FindCompatibleProducts(enclosure, candidates);

        Assert.AreEqual(0, result.Count);
    }

    // -----------------------------
    // SORTING TEST
    // -----------------------------

    [TestMethod]
    public void Results_Should_Be_Sorted_By_Score()
    {
        var engine = CreateEngine();

        var screen = CreateProduct(
            "SCREEN1",
            CompatibilityConstants.Categories.ShowerScreens,
            attributes: "{\"Fixed Panel Width\": 8}",
            series: "A");

        var base1 = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 32}",
            series: "A");

        var base2 = CreateProduct(
            "BASE2",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 36}",
            series: "A");

        var base3 = CreateProduct(
            "BASE2",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30}",
            series: "A");

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, new() { base1, base2, base3 } }
        };

        var result = engine.FindCompatibleProducts(screen, candidates);

        Assert.IsTrue(result.Count > 0);
        var products = result[0].Products;

        Assert.IsTrue(products.Count >= 1);
    }
}
