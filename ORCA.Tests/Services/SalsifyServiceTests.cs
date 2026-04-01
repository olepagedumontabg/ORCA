using ClosedXML.Excel;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Moq;
using Moq.Protected;
using ORCA.Api.Data;
using ORCA.Api.Domain.Entities;
using ORCA.Api.Services;
using System.Net;
using System.Reflection;
using System.Text;

namespace ORCA.Tests.Services;

[TestClass]
public class SalsifyServiceTests
{
    // -----------------------------
    // Helpers
    // -----------------------------

    private OrcaDbContext CreateDb()
    {
        var options = new DbContextOptionsBuilder<OrcaDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        return new OrcaDbContext(options);
    }

    private IServiceScopeFactory CreateScopeFactory(
        OrcaDbContext db,
        ICompatibilityService compatibilityService)
    {
        var providerMock = new Mock<IServiceProvider>();

        providerMock.Setup(p => p.GetService(typeof(OrcaDbContext)))
            .Returns(db);

        providerMock.Setup(p => p.GetService(typeof(ICompatibilityService)))
            .Returns(compatibilityService);

        var scopeMock = new Mock<IServiceScope>();
        scopeMock.Setup(s => s.ServiceProvider)
            .Returns(providerMock.Object);

        var factoryMock = new Mock<IServiceScopeFactory>();
        factoryMock.Setup(f => f.CreateScope())
            .Returns(scopeMock.Object);

        return factoryMock.Object;
    }

    private HttpClient CreateHttpClient(byte[] response)
    {
        var handlerMock = new Mock<HttpMessageHandler>();

        handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>(
                "SendAsync",
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new ByteArrayContent(response)
            });

        return new HttpClient(handlerMock.Object);
    }

    private byte[] CreateExcel(params (string sku, string name)[] rows)
    {
        using var wb = new XLWorkbook();
        var ws = wb.AddWorksheet("Category1");

        ws.Cell(1, 1).Value = "Unique ID";
        ws.Cell(1, 2).Value = "Product Name";

        int r = 2;
        foreach (var row in rows)
        {
            ws.Cell(r, 1).Value = row.sku;
            ws.Cell(r, 2).Value = row.name;
            r++;
        }

        using var ms = new MemoryStream();
        wb.SaveAs(ms);
        return ms.ToArray();
    }

    private async Task InvokePrivateRunSync(SalsifyService service, int syncId, string url)
    {
        var method = typeof(SalsifyService)
            .GetMethod("RunSyncAsync", BindingFlags.NonPublic | BindingFlags.Instance);

        var task = (Task)method.Invoke(service, new object[] { syncId, url });
        await task;
    }

    // -----------------------------
    // TESTS
    // -----------------------------

    [TestMethod]
    public async Task ProcessWebhookAsync_Should_Create_Record()
    {
        var db = CreateDb();

        var compatMock = new Mock<ICompatibilityService>();

        var scopeFactory = CreateScopeFactory(db, compatMock.Object);

        var httpClient = CreateHttpClient(Array.Empty<byte>());

        var logger = new Mock<ILogger<SalsifyService>>();

        var service = new SalsifyService(scopeFactory, httpClient, logger.Object);

        var result = await service.ProcessWebhookAsync("url", "ch1", "channel");

        Assert.IsTrue(result.Success);
        Assert.IsTrue(result.SyncId > 0);

        var record = db.SyncStatuses.FirstOrDefault();
        Assert.IsNotNull(record);
        Assert.AreEqual("queued", record.Status);
    }

    [TestMethod]
    public async Task RunSync_Should_Add_New_Product()
    {
        var db = CreateDb();

        var excel = CreateExcel(("SKU1", "Product 1"));

        var compatMock = new Mock<ICompatibilityService>();

        var scopeFactory = CreateScopeFactory(db, compatMock.Object);

        var httpClient = CreateHttpClient(excel);

        var logger = new Mock<ILogger<SalsifyService>>();

        var service = new SalsifyService(scopeFactory, httpClient, logger.Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        Assert.AreEqual(1, db.Products.Count());
        Assert.AreEqual("SKU1", db.Products.First().Sku);
    }

    [TestMethod]
    public async Task RunSync_Should_Update_Existing_Product()
    {
        var db = CreateDb();

        db.Products.Add(new Product
        {
            Sku = "SKU1",
            ProductName = "Old Name",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        });

        await db.SaveChangesAsync();

        var excel = CreateExcel(("SKU1", "New Name"));

        var compatMock = new Mock<ICompatibilityService>();

        var scopeFactory = CreateScopeFactory(db, compatMock.Object);

        var httpClient = CreateHttpClient(excel);

        var service = new SalsifyService(scopeFactory, httpClient, new Mock<ILogger<SalsifyService>>().Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        var product = db.Products.First();
        Assert.AreEqual("New Name", product.ProductName);
    }

    [TestMethod]
    public async Task RunSync_Should_Delete_Missing_Product()
    {
        var db = CreateDb();

        db.Products.Add(new Product
        {
            Sku = "OLDSKU",
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        });

        await db.SaveChangesAsync();

        var excel = CreateExcel(("SKU1", "Product 1"));

        var scopeFactory = CreateScopeFactory(db, new Mock<ICompatibilityService>().Object);

        var service = new SalsifyService(scopeFactory, CreateHttpClient(excel), new Mock<ILogger<SalsifyService>>().Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        Assert.AreEqual(1, db.Products.Count());
        Assert.AreEqual("SKU1", db.Products.First().Sku);
    }

    [TestMethod]
    public async Task RunSync_Should_Call_Compatibility_Service()
    {
        var db = CreateDb();

        var excel = CreateExcel(("SKU1", "Product 1"));

        var compatMock = new Mock<ICompatibilityService>();

        var scopeFactory = CreateScopeFactory(db, compatMock.Object);

        var service = new SalsifyService(scopeFactory, CreateHttpClient(excel), new Mock<ILogger<SalsifyService>>().Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        compatMock.Verify(c => c.ComputeCompatibilitiesAsync("SKU1"), Times.Once);
    }

    [TestMethod]
    public async Task RunSync_Should_Set_Status_To_Completed()
    {
        var db = CreateDb();

        var excel = CreateExcel(("SKU1", "Product 1"));

        var scopeFactory = CreateScopeFactory(db, new Mock<ICompatibilityService>().Object);

        var service = new SalsifyService(scopeFactory, CreateHttpClient(excel), new Mock<ILogger<SalsifyService>>().Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        var updated = db.SyncStatuses.First();
        Assert.AreEqual("completed", updated.Status);
        Assert.IsNotNull(updated.CompletedAt);
    }

    [TestMethod]
    public async Task RunSync_Should_Set_Status_To_Failed_On_Error()
    {
        var db = CreateDb();

        var httpClient = new HttpClient(new FailingHandler());

        var scopeFactory = CreateScopeFactory(db, new Mock<ICompatibilityService>().Object);

        var service = new SalsifyService(scopeFactory, httpClient, new Mock<ILogger<SalsifyService>>().Object);

        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        db.SyncStatuses.Add(sync);
        await db.SaveChangesAsync();

        await InvokePrivateRunSync(service, sync.Id, "url");

        var updated = db.SyncStatuses.First();
        Assert.AreEqual("failed", updated.Status);
        Assert.IsNotNull(updated.ErrorMessage);
    }

    [TestMethod]
    public async Task CleanupAsync_Should_Delete_Old_Records()
    {
        var db = CreateDb();

        db.SyncStatuses.Add(new SyncStatus
        {
            Status = "completed",
            StartedAt = DateTime.UtcNow.AddDays(-10)
        });

        await db.SaveChangesAsync();

        var service = new SalsifyService(
            CreateScopeFactory(db, new Mock<ICompatibilityService>().Object),
            new HttpClient(),
            new Mock<ILogger<SalsifyService>>().Object);

        var result = await service.CleanupAsync(5);

        Assert.AreEqual(1, result.DeletedCount);
    }

    // -----------------------------
    // Fake handler erreur HTTP
    // -----------------------------

    private class FailingHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            throw new Exception("HTTP failure");
        }
    }
}