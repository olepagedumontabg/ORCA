using Microsoft.AspNetCore.Mvc;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Moq;
using ORCA.Api.Controllers;
using ORCA.Api.DTOs;
using ORCA.Api.Services.Interface;

namespace ORCA.Tests.Controller;

[TestClass]
public class CompatibilityControllerTests
{
    private Mock<ICompatibilityService> _compatibilityServiceMock;
    private Mock<IProductService> _productServiceMock;
    private CompatibilityController _controller;

    [TestInitialize]
    public void Setup()
    {
        _compatibilityServiceMock = new Mock<ICompatibilityService>();
        _productServiceMock = new Mock<IProductService>();
        _controller = new CompatibilityController(
            _compatibilityServiceMock.Object,
            _productServiceMock.Object);
    }

    // ─── GetCompatible ────────────────────────────────────────────────────────

    [TestMethod]
    public async Task GetCompatible_Returns200_WhenProductFound()
    {
        _compatibilityServiceMock
            .Setup(x => x.GetCompatibleProductsAsync("SKU1", null, null, null))
            .ReturnsAsync(new CompatibilityResultDto { Success = true });

        var result = await _controller.GetCompatible("SKU1");

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }

    [TestMethod]
    public async Task GetCompatible_Returns404_WhenProductNotFound()
    {
        _compatibilityServiceMock
            .Setup(x => x.GetCompatibleProductsAsync("NOTFOUND", null, null, null))
            .ReturnsAsync(new CompatibilityResultDto { Success = false, ErrorMessage = "Product not found: NOTFOUND" });

        var result = await _controller.GetCompatible("NOTFOUND");

        Assert.IsInstanceOfType(result, typeof(NotFoundObjectResult));
    }

    [TestMethod]
    public async Task GetCompatible_Passes_Filters_To_Service()
    {
        _compatibilityServiceMock
            .Setup(x => x.GetCompatibleProductsAsync("SKU1", "Walls", "MAAX", "SeriesX"))
            .ReturnsAsync(new CompatibilityResultDto { Success = true });

        var result = await _controller.GetCompatible("SKU1", category: "Walls", brand: "MAAX", serie: "SeriesX");

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
        _compatibilityServiceMock.Verify(
            x => x.GetCompatibleProductsAsync("SKU1", "Walls", "MAAX", "SeriesX"),
            Times.Once);
    }

    // ─── Search ───────────────────────────────────────────────────────────────

    [TestMethod]
    public async Task Search_Returns400_WhenSkuIsEmpty()
    {
        var result = await _controller.Search(new CompatibilitySearchRequest { Sku = "" });

        Assert.IsInstanceOfType(result, typeof(BadRequestObjectResult));
        _compatibilityServiceMock.Verify(x => x.SearchAsync(It.IsAny<CompatibilitySearchRequest>()), Times.Never);
    }

    [TestMethod]
    public async Task Search_Returns400_WhenSkuIsWhitespace()
    {
        var result = await _controller.Search(new CompatibilitySearchRequest { Sku = "   " });

        Assert.IsInstanceOfType(result, typeof(BadRequestObjectResult));
    }

    [TestMethod]
    public async Task Search_Returns200_WhenProductFound()
    {
        _compatibilityServiceMock
            .Setup(x => x.SearchAsync(It.IsAny<CompatibilitySearchRequest>()))
            .ReturnsAsync(new CompatibilityResultDto { Success = true });

        var result = await _controller.Search(new CompatibilitySearchRequest { Sku = "SKU1" });

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }

    [TestMethod]
    public async Task Search_Returns404_WhenProductNotFound()
    {
        _compatibilityServiceMock
            .Setup(x => x.SearchAsync(It.IsAny<CompatibilitySearchRequest>()))
            .ReturnsAsync(new CompatibilityResultDto { Success = false, ErrorMessage = "Not found" });

        var result = await _controller.Search(new CompatibilitySearchRequest { Sku = "NOTFOUND" });

        Assert.IsInstanceOfType(result, typeof(NotFoundObjectResult));
    }

    // ─── Compute ──────────────────────────────────────────────────────────────

    [TestMethod]
    public async Task Compute_Returns200_WhenSuccess()
    {
        _compatibilityServiceMock
            .Setup(x => x.ComputeCompatibilitiesAsync("SKU1"))
            .ReturnsAsync(new CompatibilityResultDto { Success = true });

        var result = await _controller.Compute("SKU1");

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }

    [TestMethod]
    public async Task Compute_Returns404_WhenProductNotFound()
    {
        _compatibilityServiceMock
            .Setup(x => x.ComputeCompatibilitiesAsync("NOTFOUND"))
            .ReturnsAsync(new CompatibilityResultDto { Success = false, ErrorMessage = "Product not found: NOTFOUND" });

        var result = await _controller.Compute("NOTFOUND");

        Assert.IsInstanceOfType(result, typeof(NotFoundObjectResult));
    }

    // ─── GetCategories ────────────────────────────────────────────────────────

    [TestMethod]
    public async Task GetCategories_Returns200_WithCategoryList()
    {
        _productServiceMock
            .Setup(x => x.GetCategoriesAsync())
            .ReturnsAsync(new List<(string Category, int Count)>
            {
                ("Shower Bases", 10),
                ("Bathtubs", 5)
            });

        var result = await _controller.GetCategories();

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }

    [TestMethod]
    public async Task GetCategories_Returns200_WithEmptyList()
    {
        _productServiceMock
            .Setup(x => x.GetCategoriesAsync())
            .ReturnsAsync(new List<(string Category, int Count)>());

        var result = await _controller.GetCategories();

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }

    [TestMethod]
    public async Task GetCompatibilityCategories_Returns200_WithCategoryList()
    {
        _productServiceMock
            .Setup(x => x.GetCategoriesAsync())
            .ReturnsAsync(new List<(string Category, int Count)>
            {
                ("Walls", 8)
            });

        var result = await _controller.GetCompatibilityCategories();

        Assert.IsInstanceOfType(result, typeof(OkObjectResult));
    }
}
