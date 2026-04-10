using Microsoft.VisualStudio.TestTools.UnitTesting;
using Moq;
using Microsoft.Extensions.Logging;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Services;
using ORCA.Api.Services.Interface;
using ORCA.Api.Domain.Constants;
using ORCA.Api.Domain.Entities;
using ORCA.Api.DTOs;
using ORCA.Api.Data;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace ORCA.Tests.Services
{
    [TestClass]
    public class CompatibilityServiceTests
    {
        private OrcaDbContext _db;
        private Mock<IProductService> _productServiceMock;
        private Mock<ICompatibilityEngine> _engineMock;
        private Mock<ILogger<CompatibilityService>> _loggerMock;
        private CompatibilityService _service;

        [TestInitialize]
        public void Setup()
        {
            var options = new DbContextOptionsBuilder<OrcaDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString())
                .Options;

            _db = new OrcaDbContext(options);

            _productServiceMock = new Mock<IProductService>();
            _engineMock = new Mock<ICompatibilityEngine>();
            _loggerMock = new Mock<ILogger<CompatibilityService>>();

            _service = new CompatibilityService(
                _db,
                _productServiceMock.Object,
                _engineMock.Object,
                _loggerMock.Object);
        }

        // =============================
        // 🔴 BASIC CASES
        // =============================

        [TestMethod]
        public async Task GetCompatible_ProductNotFound_ReturnsError()
        {
            _productServiceMock
                .Setup(x => x.GetBySkuAsync(It.IsAny<string>()))
                .ReturnsAsync((Product?)null);

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsFalse(result.Success);
            Assert.IsNotNull(result.ErrorMessage);
        }

        [TestMethod]
        public async Task GetCompatible_DotNotationFallback_IsRemoved()
        {
            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC.001"))
                .ReturnsAsync((Product?)null);

            var result = await _service.GetCompatibleProductsAsync("ABC.001");

            Assert.IsFalse(result.Success);
            _productServiceMock.Verify(x => x.GetBySkuAsync("ABC"), Times.Never);
        }

        // =============================
        // 🟢 PRECOMPUTED
        // =============================

        [TestMethod]
        public async Task GetCompatible_UsesAlternateId1_WhenNoPrecomputedData()
        {
            var product    = new Product { Id = 1, Sku = "ABC",  Category = "Doors", AlternateId1 = "ALT1" };
            var altProduct = new Product { Id = 2, Sku = "ALT1", Category = "Doors" };
            var compatible = new Product { Id = 3, Sku = "DEF",  Category = "Doors" };

            _db.Products.AddRange(product, altProduct, compatible);
            _db.ProductCompatibilities.Add(new ProductCompatibility
            {
                BaseProductId = 2,
                CompatibleProductId = 3,
            });
            await _db.SaveChangesAsync();

            _productServiceMock.Setup(x => x.GetBySkuAsync("ABC")).ReturnsAsync(product);
            _productServiceMock.Setup(x => x.GetBySkuAsync("ALT1")).ReturnsAsync(altProduct);

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.AreEqual("database", result.DataSource);
            Assert.IsTrue(result.Compatibles.Any(c => c.Products.Any(p => p.Sku == "DEF")));
        }

        [TestMethod]
        public async Task GetCompatible_CascadesToAlternateId2_WhenAlternateId1HasNoData()
        {
            var product     = new Product { Id = 1, Sku = "ABC",  Category = "Doors", AlternateId1 = "ALT1", AlternateId2 = "ALT2" };
            var altProduct  = new Product { Id = 2, Sku = "ALT1", Category = "Doors" };
            var alt2Product = new Product { Id = 3, Sku = "ALT2", Category = "Doors" };
            var compatible  = new Product { Id = 4, Sku = "DEF",  Category = "Doors" };

            _db.Products.AddRange(product, altProduct, alt2Product, compatible);
            _db.ProductCompatibilities.Add(new ProductCompatibility
            {
                BaseProductId = 3,
                CompatibleProductId = 4,
            });
            await _db.SaveChangesAsync();

            _productServiceMock.Setup(x => x.GetBySkuAsync("ABC")).ReturnsAsync(product);
            _productServiceMock.Setup(x => x.GetBySkuAsync("ALT1")).ReturnsAsync(altProduct);
            _productServiceMock.Setup(x => x.GetBySkuAsync("ALT2")).ReturnsAsync(alt2Product);

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.AreEqual("database", result.DataSource);
            Assert.IsTrue(result.Compatibles.Any(c => c.Products.Any(p => p.Sku == "DEF")));
        }

        [TestMethod]
        public async Task GetCompatible_ComputesOnDemand_WhenAllAlternatesHaveNoData()
        {
            var product    = new Product { Id = 1, Sku = "ABC",  Category = "Doors", AlternateId1 = "ALT1" };
            var altProduct = new Product { Id = 2, Sku = "ALT1", Category = "Doors" };

            _productServiceMock.Setup(x => x.GetBySkuAsync("ABC")).ReturnsAsync(product);
            _productServiceMock.Setup(x => x.GetBySkuAsync("ALT1")).ReturnsAsync(altProduct);
            _productServiceMock
                .Setup(x => x.GetProductsByCategoriesAsync(It.IsAny<string[]>()))
                .ReturnsAsync(new List<Product>());
            _engineMock
                .Setup(x => x.FindCompatibleProducts(It.IsAny<Product>(), It.IsAny<Dictionary<string, List<Product>>>()))
                .Returns(new List<CompatibilityCategoryResult>());

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.AreEqual("computed", result.DataSource);
        }

        [TestMethod]
        public async Task GetCompatible_UsesPrecomputedData()
        {
            var product = new Product { Id = 1, Sku = "ABC", Category = "Doors" };
            var compatible = new Product { Id = 2, Sku = "DEF", Category = "Doors" };

            _db.Products.AddRange(product, compatible);
            _db.ProductCompatibilities.Add(new ProductCompatibility
            {
                BaseProductId = 1,
                CompatibleProductId = 2,
            });

            await _db.SaveChangesAsync();

            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC"))
                .ReturnsAsync(product);

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.AreEqual("database", result.DataSource);
            Assert.IsTrue(result.Compatibles.Any());
        }

        // =============================
        // 🟡 COMPUTE FALLBACK
        // =============================

        [TestMethod]
        public async Task GetCompatible_ComputesWhenNoPrecomputed()
        {
            var product = new Product { Id = 1, Sku = "ABC", Category = "Doors" };

            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC"))
                .ReturnsAsync(product);

            _productServiceMock
                .Setup(x => x.GetProductsByCategoriesAsync(It.IsAny<string[]>()))
                .ReturnsAsync(new List<Product>());

            _engineMock
                .Setup(x => x.FindCompatibleProducts(
                    It.IsAny<Product>(),
                    It.IsAny<Dictionary<string, List<Product>>>()))
                .Returns(new List<CompatibilityCategoryResult>());

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.AreEqual("computed", result.DataSource);
        }

        // =============================
        // 🔵 FILTERS
        // =============================

        [TestMethod]
        public async Task GetCompatible_AppliesBrandFilter()
        {
            var product = new Product { Id = 1, Sku = "ABC", Category = CompatibilityConstants.Categories.ShowerBases };

            var compatibleProduct = new Product
            {
                Id = 2,
                Sku = "DEF",
                Category = CompatibilityConstants.Categories.ShowerDoors,
                Brand = "MAAX"
            };

            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC"))
                .ReturnsAsync(product);

            _productServiceMock
                .Setup(x => x.GetProductsByCategoriesAsync(It.IsAny<string[]>()))
                .ReturnsAsync(new List<Product> { compatibleProduct });

            _engineMock
                .Setup(x => x.FindCompatibleProducts(It.IsAny<Product>(), It.IsAny<Dictionary<string, List<Product>>>()))
                .Returns(new List<CompatibilityCategoryResult>
                {
                    new CompatibilityCategoryResult
                    {
                        Category = CompatibilityConstants.Categories.ShowerDoors,
                        Products = new List<CompatibleProductDto>
                        {
                            new CompatibleProductDto
                            {
                                Sku = "DEF",
                                Brand = "MAAX"
                            },
                            new CompatibleProductDto
                            {
                                Sku = "GHI",
                                Brand = "OTHER"
                            }
                        }
                    }
                });

            var result = await _service.GetCompatibleProductsAsync("ABC", brandFilter: "MAAX");

            Assert.IsTrue(result.Success);
            Assert.IsTrue(result.Compatibles.Any());
            Assert.IsTrue(result.Compatibles.All(c => c.Products.All(p => p.Brand == "MAAX")));
        }

        // =============================
        // 🟣 COMPUTE + SAVE
        // =============================

        [TestMethod]
        public async Task ComputeCompatibilities_SavesResults()
        {
            var product = new Product { Id = 1, Sku = "ABC", Category = CompatibilityConstants.Categories.ShowerBases };
            var compatible = new Product { Id = 2, Sku = "DEF", Category = CompatibilityConstants.Categories.ShowerDoors };

            _db.Products.AddRange(product, compatible);
            await _db.SaveChangesAsync();

            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC"))
                .ReturnsAsync(product);

            _productServiceMock
                .Setup(x => x.GetProductsByCategoriesAsync(It.IsAny<string[]>()))
                .ReturnsAsync(new List<Product> { compatible });

            _engineMock
                .Setup(x => x.FindCompatibleProducts(It.IsAny<Product>(), It.IsAny<Dictionary<string, List<Product>>>()))
                .Returns(new List<CompatibilityCategoryResult>
                {
                    new CompatibilityCategoryResult
                    {
                        Category = CompatibilityConstants.Categories.ShowerDoors,
                        Products = new List<CompatibleProductDto>
                        {
                            new CompatibleProductDto
                            {
                                Sku = "DEF"
                            }
                        }
                    }
                });

            var result = await _service.ComputeCompatibilitiesAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.IsTrue(_db.ProductCompatibilities.Any());
        }

        // =============================
        // 🟤 OVERRIDES
        // =============================

        [TestMethod]
        public async Task GetCompatible_AppliesBlacklistOverride()
        {
            var product = new Product { Id = 1, Sku = "ABC", Category = CompatibilityConstants.Categories.ShowerBases };
            var compatible = new Product { Id = 2, Sku = "DEF", Category = CompatibilityConstants.Categories.ShowerDoors };

            _db.Products.AddRange(product, compatible);

            _db.CompatibilityOverrides.Add(new CompatibilityOverride
            {
                BaseSku = "ABC",
                CompatibleSku = "DEF",
                OverrideType = "blacklist"
            });

            await _db.SaveChangesAsync();

            _productServiceMock
                .Setup(x => x.GetBySkuAsync("ABC"))
                .ReturnsAsync(product);

            _productServiceMock
                .Setup(x => x.GetProductsByCategoriesAsync(It.IsAny<string[]>()))
                .ReturnsAsync(new List<Product> { compatible });

            _engineMock
                .Setup(x => x.FindCompatibleProducts(It.IsAny<Product>(), It.IsAny<Dictionary<string, List<Product>>>()))
                .Returns(new List<CompatibilityCategoryResult>
                {
                    new CompatibilityCategoryResult
                    {
                        Category = CompatibilityConstants.Categories.ShowerDoors,
                        Products = new List<CompatibleProductDto>
                        {
                            new CompatibleProductDto { Sku = "DEF" }
                        }
                    }
                });

            var result = await _service.GetCompatibleProductsAsync("ABC");

            Assert.IsTrue(result.Success);
            Assert.IsFalse(result.Compatibles.Any(c => c.Products.Any(p => p.Sku == "DEF")));
        }
    }
}
