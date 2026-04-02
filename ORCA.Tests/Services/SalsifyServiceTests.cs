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
using ORCA.Api.Services.Interface;
using System.Net;
using System.Reflection;

namespace ORCA.Tests.Services;

[TestClass]
public class SalsifyServiceTests
{
    // ─── helpers ──────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns DbContextOptions backed by a named in-memory database.
    /// Every call to CreateContext() with the SAME name shares data,
    /// but each call produces a FRESH DbContext instance — avoiding the
    /// "second operation on same context" concurrency error that occurs
    /// when the service's fire-and-forget scope and the test both hold
    /// a reference to the exact same object.
    /// </summary>
    private static DbContextOptions<OrcaDbContext> DbOptions(string name) =>
        new DbContextOptionsBuilder<OrcaDbContext>()
            .UseInMemoryDatabase(name)
            .Options;

    private static OrcaDbContext CreateContext(DbContextOptions<OrcaDbContext> opts) =>
        new(opts);

    /// <summary>
    /// Scope factory where each CreateScope() call creates a brand-new
    /// OrcaDbContext instance backed by the shared in-memory database.
    /// This mirrors real DI behaviour (scoped lifetime = new instance per scope).
    /// </summary>
    private static IServiceScopeFactory CreateScopeFactory(
        DbContextOptions<OrcaDbContext> opts,
        ICompatibilityService compatibilityService)
    {
        var factoryMock = new Mock<IServiceScopeFactory>();

        factoryMock.Setup(f => f.CreateScope())
            .Returns(() =>
            {
                var db = new OrcaDbContext(opts);

                var providerMock = new Mock<IServiceProvider>();
                providerMock.Setup(p => p.GetService(typeof(OrcaDbContext))).Returns(db);
                providerMock.Setup(p => p.GetService(typeof(ICompatibilityService))).Returns(compatibilityService);

                var scopeMock = new Mock<IServiceScope>();
                scopeMock.Setup(s => s.ServiceProvider).Returns(providerMock.Object);

                return scopeMock.Object;
            });

        return factoryMock.Object;
    }

    private static HttpClient CreateHttpClient(byte[] response)
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

    private static byte[] CreateExcel(params (string sku, string name)[] rows)
    {
        using var wb = new XLWorkbook();
        var ws = wb.AddWorksheet("Category1");
        ws.Cell(1, 1).Value = "Unique ID";
        ws.Cell(1, 2).Value = "Product Name";
        int r = 2;
        foreach (var (sku, name) in rows)
        {
            ws.Cell(r, 1).Value = sku;
            ws.Cell(r, 2).Value = name;
            r++;
        }
        using var ms = new MemoryStream();
        wb.SaveAs(ms);
        return ms.ToArray();
    }

    private static async Task InvokeRunSyncAsync(SalsifyService service, int syncId, string url)
    {
        var method = typeof(SalsifyService)
            .GetMethod("RunSyncAsync", BindingFlags.NonPublic | BindingFlags.Instance)!;
        await (Task)method.Invoke(service, [syncId, url])!;
    }

    // ─── ProcessWebhookAsync ───────────────────────────────────────────────────

    [TestMethod]
    public async Task ProcessWebhookAsync_Should_Return_Success_And_Create_SyncRecord()
    {
        var opts = DbOptions(nameof(ProcessWebhookAsync_Should_Return_Success_And_Create_SyncRecord));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient([]), new Mock<ILogger<SalsifyService>>().Object);

        var result = await service.ProcessWebhookAsync("http://test/feed", "ch1", "channel");

        Assert.IsTrue(result.Success);
        Assert.IsTrue(result.SyncId > 0);

        // Give the fire-and-forget background task a moment, then verify a record exists.
        await Task.Delay(200);
        await using var ctx = CreateContext(opts);
        Assert.IsTrue(await ctx.SyncStatuses.AnyAsync(s => s.Id == result.SyncId));
    }

    // ─── RunSyncAsync (private, invoked via reflection) ───────────────────────

    [TestMethod]
    public async Task RunSync_Should_Add_New_Product()
    {
        var opts = DbOptions(nameof(RunSync_Should_Add_New_Product));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient(CreateExcel(("SKU1", "Product 1"))), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        await using var verify = CreateContext(opts);
        Assert.AreEqual(1, await verify.Products.CountAsync());
        Assert.AreEqual("SKU1", (await verify.Products.FirstAsync()).Sku);
    }

    [TestMethod]
    public async Task RunSync_Should_Update_Existing_Product()
    {
        var opts = DbOptions(nameof(RunSync_Should_Update_Existing_Product));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient(CreateExcel(("SKU1", "New Name"))), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        setup.Products.Add(new Product { Sku = "SKU1", ProductName = "Old Name", Category = "", CreatedAt = DateTime.UtcNow, UpdatedAt = DateTime.UtcNow });
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        await using var verify = CreateContext(opts);
        var product = await verify.Products.FirstAsync();
        Assert.AreEqual("New Name", product.ProductName);
    }

    [TestMethod]
    public async Task RunSync_Should_Delete_Missing_Product()
    {
        var opts = DbOptions(nameof(RunSync_Should_Delete_Missing_Product));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient(CreateExcel(("SKU1", "Product 1"))), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        setup.Products.Add(new Product { Sku = "OLDSKU", Category = "", CreatedAt = DateTime.UtcNow, UpdatedAt = DateTime.UtcNow });
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        await using var verify = CreateContext(opts);
        Assert.AreEqual(1, await verify.Products.CountAsync());
        Assert.AreEqual("SKU1", (await verify.Products.FirstAsync()).Sku);
    }

    [TestMethod]
    public async Task RunSync_Should_Call_Compatibility_Service_For_Each_Changed_Sku()
    {
        var opts = DbOptions(nameof(RunSync_Should_Call_Compatibility_Service_For_Each_Changed_Sku));
        var compatMock = new Mock<ICompatibilityService>();
        var scopeFactory = CreateScopeFactory(opts, compatMock.Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient(CreateExcel(("SKU1", "Product 1"))), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        compatMock.Verify(c => c.ComputeCompatibilitiesAsync("SKU1"), Times.Once);
    }

    [TestMethod]
    public async Task RunSync_Should_Set_Status_To_Completed()
    {
        var opts = DbOptions(nameof(RunSync_Should_Set_Status_To_Completed));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, CreateHttpClient(CreateExcel(("SKU1", "Product 1"))), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        await using var verify = CreateContext(opts);
        var record = await verify.SyncStatuses.FirstAsync();
        Assert.AreEqual("completed", record.Status);
        Assert.IsNotNull(record.CompletedAt);
    }

    [TestMethod]
    public async Task RunSync_Should_Set_Status_To_Failed_On_Http_Error()
    {
        var opts = DbOptions(nameof(RunSync_Should_Set_Status_To_Failed_On_Http_Error));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, new HttpClient(new FailingHandler()), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        var sync = new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow };
        setup.SyncStatuses.Add(sync);
        await setup.SaveChangesAsync();

        await InvokeRunSyncAsync(service, sync.Id, "http://test/feed");

        await using var verify = CreateContext(opts);
        var record = await verify.SyncStatuses.FirstAsync();
        Assert.AreEqual("failed", record.Status);
        Assert.IsNotNull(record.ErrorMessage);
    }

    // ─── CleanupAsync ─────────────────────────────────────────────────────────

    [TestMethod]
    public async Task CleanupAsync_Should_Delete_Old_Completed_Records()
    {
        var opts = DbOptions(nameof(CleanupAsync_Should_Delete_Old_Completed_Records));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, new HttpClient(), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        setup.SyncStatuses.Add(new SyncStatus { Status = "completed", StartedAt = DateTime.UtcNow.AddDays(-10) });
        setup.SyncStatuses.Add(new SyncStatus { Status = "completed", StartedAt = DateTime.UtcNow.AddDays(-1) });
        await setup.SaveChangesAsync();

        var result = await service.CleanupAsync(5);

        Assert.AreEqual(1, result.DeletedCount);

        await using var verify = CreateContext(opts);
        Assert.AreEqual(1, await verify.SyncStatuses.CountAsync());
    }

    [TestMethod]
    public async Task CleanupAsync_Should_Not_Delete_Recent_Records()
    {
        var opts = DbOptions(nameof(CleanupAsync_Should_Not_Delete_Recent_Records));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, new HttpClient(), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        setup.SyncStatuses.Add(new SyncStatus { Status = "completed", StartedAt = DateTime.UtcNow.AddDays(-1) });
        await setup.SaveChangesAsync();

        var result = await service.CleanupAsync(5);

        Assert.AreEqual(0, result.DeletedCount);
        await using var verify = CreateContext(opts);
        Assert.AreEqual(1, await verify.SyncStatuses.CountAsync());
    }

    [TestMethod]
    public async Task CleanupAsync_Should_Not_Delete_Queued_Or_Running_Records()
    {
        var opts = DbOptions(nameof(CleanupAsync_Should_Not_Delete_Queued_Or_Running_Records));
        var scopeFactory = CreateScopeFactory(opts, new Mock<ICompatibilityService>().Object);
        var service = new SalsifyService(scopeFactory, new HttpClient(), new Mock<ILogger<SalsifyService>>().Object);

        await using var setup = CreateContext(opts);
        setup.SyncStatuses.AddRange(
            new SyncStatus { Status = "queued", StartedAt = DateTime.UtcNow.AddDays(-10) },
            new SyncStatus { Status = "running", StartedAt = DateTime.UtcNow.AddDays(-10) });
        await setup.SaveChangesAsync();

        var result = await service.CleanupAsync(5);

        Assert.AreEqual(0, result.DeletedCount);
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private sealed class FailingHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken cancellationToken) =>
            throw new HttpRequestException("Simulated HTTP failure");
    }
}
