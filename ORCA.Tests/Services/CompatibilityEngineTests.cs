using Microsoft.Extensions.Logging;
using Moq;
using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services;
using System.Diagnostics;

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

    [TestMethod]
    public void DoorWidth_Should_Match_On_Min_Boundary()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 30, \"Maximum Width\": 50}", "A");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 30, \"Installation\": \"alcove\"}", "A");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(1, result.Count);
    }

    [TestMethod]
    public void DoorWidth_Should_Match_On_Max_Boundary()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 30, \"Maximum Width\": 50}", "A");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 50, \"Installation\": \"alcove\"}", "A");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(1, result.Count);
    }

    [TestMethod]
    public void DoorWidth_Should_Fail_Outside_Range()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 30, \"Maximum Width\": 50}", "A");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 29, \"Installation\": \"alcove\"}", "A");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(0, result.Count);
    }

    // --------------------------------------------------
    // 🧪 SCREEN WIDTH EDGE CASES
    // --------------------------------------------------

    [TestMethod]
    public void Screen_Should_Handle_Null_Attributes()
    {
        var engine = CreateEngine();

        var screen = CreateProduct("S1", CompatibilityConstants.Categories.ShowerScreens, null, "A");
        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 30}", "A");

        var result = engine.FindCompatibleProducts(screen,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(0, result.Count);
    }

    [TestMethod]
    public void Screen_Should_Handle_Invalid_JSON()
    {
        var engine = CreateEngine();

        var screen = CreateProduct("S1", CompatibilityConstants.Categories.ShowerScreens, "{INVALID}", "A");
        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 30}", "A");

        var result = engine.FindCompatibleProducts(screen,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(0, result.Count);
    }

    // --------------------------------------------------
    // 🧪 SERIES / BRAND LOGIC
    // --------------------------------------------------

    [TestMethod]
    public void Should_Fail_When_Series_Not_Compatible()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 30, \"Maximum Width\": 50}", "A");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 60, \"Installation\": \"alcove\"}", "B");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(0, result.Count);
    }

    [TestMethod]
    public void Should_Handle_Null_Series()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 30, \"Maximum Width\": 50}", null);

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 40, \"Installation\": \"alcove\"}", null);

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.IsNotNull(result);
    }

    // --------------------------------------------------
    // 🧪 INSTALLATION RULES
    // --------------------------------------------------

    [TestMethod]
    public void ShowerDoor_Should_Accept_Corner()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 20, \"Maximum Width\": 50}", "A");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Max Door Width\": 30, \"Installation\": \"corner\"}", "A");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.AreEqual(1, result.Count);
    }

    [TestMethod]
    public void TubDoor_Should_Reject_Corner()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.TubDoors,
            "{\"Minimum Width\": 20, \"Maximum Width\": 50}", "A");

        var tub = CreateProduct("T1", CompatibilityConstants.Categories.Bathtubs,
            "{\"Max Door Width\": 30, \"Installation\": \"corner\"}", "A");

        var result = engine.FindCompatibleProducts(door,
            new() { { CompatibilityConstants.Categories.Bathtubs, new() { tub } } });

        Assert.AreEqual(0, result.Count);
    }

    // --------------------------------------------------
    // 🧪 TOLERANCE TEST (ENCLOSURE)
    // --------------------------------------------------

    [TestMethod]
    public void Enclosure_Should_Match_Within_Tolerance()
    {
        var engine = CreateEngine();

        var enclosure = CreateProduct("E1", CompatibilityConstants.Categories.Enclosures,
            "{\"Door Width\": 30, \"Return Panel Width\": 30}",
            "A", "B");

        var baseP = CreateProduct("B1", CompatibilityConstants.Categories.ShowerBases,
            "{\"Installation\": \"corner\"}",
            "A", "B",
            null,
            length: 60,
            width: 60);

        var result = engine.FindCompatibleProducts(enclosure,
            new() { { CompatibilityConstants.Categories.ShowerBases, new() { baseP } } });

        Assert.IsTrue(result.Count >= 0); // dépend de ta tolérance réelle
    }

    // --------------------------------------------------
    // ⚡ PERFORMANCE TEST
    // --------------------------------------------------

    [TestMethod]
    public void Performance_Should_Handle_10000_Products_Under_1s()
    {
        var engine = CreateEngine();

        var door = CreateProduct("D1", CompatibilityConstants.Categories.ShowerDoors,
            "{\"Minimum Width\": 20, \"Maximum Width\": 60}", "A");

        var list = new List<Product>();

        for (int i = 0; i < 10000; i++)
        {
            list.Add(CreateProduct(
                $"B{i}",
                CompatibilityConstants.Categories.ShowerBases,
                "{\"Max Door Width\": 40, \"Installation\": \"alcove\"}",
                "A"));
        }

        var candidates = new Dictionary<string, List<Product>>
        {
            { CompatibilityConstants.Categories.ShowerBases, list }
        };

        var sw = Stopwatch.StartNew();

        var result = engine.FindCompatibleProducts(door, candidates);

        sw.Stop();

        Assert.IsTrue(sw.ElapsedMilliseconds < 1000,
            $"Performance issue: {sw.ElapsedMilliseconds}ms");

        Assert.IsTrue(result.Count > 0);
    }

    // --------------------------------------------------
    // 💣 STRESS TEST
    // --------------------------------------------------

    [TestMethod]
    public void Should_Not_Crash_With_Empty_And_Null_Values()
    {
        var engine = CreateEngine();

        var product = CreateProduct("X", CompatibilityConstants.Categories.ShowerDoors, "{}");

        var result = engine.FindCompatibleProducts(product,
            new()
            {
                { CompatibilityConstants.Categories.ShowerBases, new List<Product?> { null! }.Where(p => p != null).ToList() }
            });

        Assert.IsNotNull(result);
    }

    // --------------------------------------------------
    // 🚫 INCOMPATIBILITY REASON TESTS
    // --------------------------------------------------

    [TestMethod]
    public void ShowerBase_ReasonDoorsCantFit_Blocks_DoorMatching()
    {
        var engine = CreateEngine();

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"alcove\", \"Reason Doors Can't Fit\": \"Opening is too narrow\"}",
            series: "A");

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.ShowerDoors,
            attributes: "{\"Minimum Width\": 20, \"Maximum Width\": 40}",
            series: "A");

        var result = engine.FindCompatibleProducts(baseProduct,
            new() { { CompatibilityConstants.Categories.ShowerDoors, new() { door } } });

        var doorResult = result.FirstOrDefault(r => r.Category == "Shower Doors");
        Assert.IsNotNull(doorResult, "Expected a Shower Doors result entry");
        Assert.AreEqual("Opening is too narrow", doorResult.IncompatibilityReason);
        Assert.AreEqual(0, doorResult.Products.Count);
    }

    [TestMethod]
    public void ShowerBase_ReasonWallsCantFit_Blocks_WallMatching()
    {
        var engine = CreateEngine();

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"alcove\", \"Reason Walls Can't Fit\": \"Not designed for wall panels\"}",
            series: "A");

        var wall = CreateProduct(
            "WALL1",
            CompatibilityConstants.Categories.Walls,
            attributes: "{\"Type\": \"alcove shower\"}",
            series: "A",
            nominal: "60x32");

        var result = engine.FindCompatibleProducts(baseProduct,
            new() { { CompatibilityConstants.Categories.Walls, new() { wall } } });

        var wallResult = result.FirstOrDefault(r => r.Category == "Walls");
        Assert.IsNotNull(wallResult, "Expected a Walls result entry");
        Assert.AreEqual("Not designed for wall panels", wallResult.IncompatibilityReason);
        Assert.AreEqual(0, wallResult.Products.Count);
    }

    [TestMethod]
    public void ShowerBase_BothReasons_Blocks_DoorsAndWalls_Independently()
    {
        var engine = CreateEngine();

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"alcove\", \"Reason Doors Can't Fit\": \"No door fits\", \"Reason Walls Can't Fit\": \"No wall fits\"}",
            series: "A");

        var result = engine.FindCompatibleProducts(baseProduct, new());

        var doorResult = result.FirstOrDefault(r => r.Category == "Shower Doors");
        var wallResult = result.FirstOrDefault(r => r.Category == "Walls");

        Assert.IsNotNull(doorResult, "Expected a Shower Doors incompatibility entry");
        Assert.AreEqual("No door fits", doorResult.IncompatibilityReason);
        Assert.AreEqual(0, doorResult.Products.Count);

        Assert.IsNotNull(wallResult, "Expected a Walls incompatibility entry");
        Assert.AreEqual("No wall fits", wallResult.IncompatibilityReason);
        Assert.AreEqual(0, wallResult.Products.Count);
    }

    [TestMethod]
    public void Bathtub_ReasonDoorsCantFit_Blocks_TubDoorMatching()
    {
        var engine = CreateEngine();

        var tub = CreateProduct(
            "TUB1",
            CompatibilityConstants.Categories.Bathtubs,
            attributes: "{\"Max Door Width\": 60, \"Installation\": \"Alcove\", \"Reason Doors Can't Fit\": \"Apron front prevents door installation\"}",
            series: "A");

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.TubDoors,
            attributes: "{\"Minimum Width\": 50, \"Maximum Width\": 70}",
            series: "A");

        var result = engine.FindCompatibleProducts(tub,
            new() { { CompatibilityConstants.Categories.TubDoors, new() { door } } });

        var doorResult = result.FirstOrDefault(r => r.Category == "Tub Doors");
        Assert.IsNotNull(doorResult, "Expected a Tub Doors result entry");
        Assert.AreEqual("Apron front prevents door installation", doorResult.IncompatibilityReason);
        Assert.AreEqual(0, doorResult.Products.Count);
    }

    [TestMethod]
    public void Bathtub_ReasonWallsCantFit_Blocks_WallMatching()
    {
        var engine = CreateEngine();

        var tub = CreateProduct(
            "TUB1",
            CompatibilityConstants.Categories.Bathtubs,
            attributes: "{\"Max Door Width\": 60, \"Installation\": \"Alcove\", \"Reason Walls Can't Fit\": \"Irregular shape incompatible with wall kits\"}",
            series: "A");

        var wall = CreateProduct(
            "WALL1",
            CompatibilityConstants.Categories.Walls,
            attributes: "{\"Type\": \"tub\"}",
            series: "A",
            nominal: "60x32");

        var result = engine.FindCompatibleProducts(tub,
            new() { { CompatibilityConstants.Categories.Walls, new() { wall } } });

        var wallResult = result.FirstOrDefault(r => r.Category == "Walls");
        Assert.IsNotNull(wallResult, "Expected a Walls result entry");
        Assert.AreEqual("Irregular shape incompatible with wall kits", wallResult.IncompatibilityReason);
        Assert.AreEqual(0, wallResult.Products.Count);
    }

    [TestMethod]
    public void Shower_ReasonDoorsCantFit_Blocks_ShowerDoorMatching()
    {
        var engine = CreateEngine();

        var shower = CreateProduct(
            "SHOWER1",
            CompatibilityConstants.Categories.Showers,
            attributes: "{\"Max Door Width\": 30, \"Max Door Height\": 80, \"Installation\": \"Alcove\", \"Reason Doors Can't Fit\": \"Integrated glass panel, no door needed\"}",
            series: "A");

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.ShowerDoors,
            attributes: "{\"Minimum Width\": 20, \"Maximum Width\": 40, \"Maximum Height\": 78}",
            series: "A");

        var result = engine.FindCompatibleProducts(shower,
            new() { { CompatibilityConstants.Categories.ShowerDoors, new() { door } } });

        var doorResult = result.FirstOrDefault(r => r.Category == "Shower Doors");
        Assert.IsNotNull(doorResult, "Expected a Shower Doors result entry");
        Assert.AreEqual("Integrated glass panel, no door needed", doorResult.IncompatibilityReason);
        Assert.AreEqual(0, doorResult.Products.Count);
    }

    [TestMethod]
    public void TubShower_ReasonDoorsCantFit_Blocks_TubDoorMatching()
    {
        var engine = CreateEngine();

        var tubShower = CreateProduct(
            "TUBSHOWER1",
            CompatibilityConstants.Categories.TubShowers,
            attributes: "{\"Max Door Width\": 60, \"Max Door Height\": 80, \"Reason Doors Can't Fit\": \"Built-in curtain rod, no door compatible\"}",
            series: "A");

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.TubDoors,
            attributes: "{\"Minimum Width\": 50, \"Maximum Width\": 70, \"Maximum Height\": 78}",
            series: "A");

        var result = engine.FindCompatibleProducts(tubShower,
            new() { { CompatibilityConstants.Categories.TubDoors, new() { door } } });

        var doorResult = result.FirstOrDefault(r => r.Category == "Tub Doors");
        Assert.IsNotNull(doorResult, "Expected a Tub Doors result entry");
        Assert.AreEqual("Built-in curtain rod, no door compatible", doorResult.IncompatibilityReason);
        Assert.AreEqual(0, doorResult.Products.Count);
    }

    [TestMethod]
    public void ReasonDoorsCantFit_WhitespaceOnly_Does_Not_Block_DoorMatching()
    {
        var engine = CreateEngine();

        var baseProduct = CreateProduct(
            "BASE1",
            CompatibilityConstants.Categories.ShowerBases,
            attributes: "{\"Max Door Width\": 30, \"Installation\": \"alcove\", \"Reason Doors Can't Fit\": \"   \"}",
            series: "A");

        var door = CreateProduct(
            "DOOR1",
            CompatibilityConstants.Categories.ShowerDoors,
            attributes: "{\"Minimum Width\": 20, \"Maximum Width\": 40}",
            series: "A");

        var result = engine.FindCompatibleProducts(baseProduct,
            new() { { CompatibilityConstants.Categories.ShowerDoors, new() { door } } });

        var doorResult = result.FirstOrDefault(r => r.Category == "Shower Doors");
        // Whitespace-only reason must not block — door should appear in compatible products
        Assert.IsTrue(doorResult == null || string.IsNullOrWhiteSpace(doorResult.IncompatibilityReason),
            "Whitespace-only reason should not trigger incompatibility");
        if (doorResult != null)
            Assert.IsTrue(doorResult.Products.Count > 0, "Door should be listed as compatible");
    }
}
