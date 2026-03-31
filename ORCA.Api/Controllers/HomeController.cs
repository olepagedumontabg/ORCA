using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;

namespace ORCA.Api.Controllers;

[ApiController]
public class HomeController : ControllerBase
{
    private readonly OrcaDbContext _db;

    public HomeController(OrcaDbContext db)
    {
        _db = db;
    }

    [HttpGet("/")]
    [HttpGet("/sync-history")]
    public async Task<ContentResult> Index()
    {
        int productCount = 0;
        int compatibilityCount = 0;
        string dbStatus = "healthy";

        try
        {
            productCount = await _db.Products.CountAsync();
            compatibilityCount = await _db.ProductCompatibilities.CountAsync();
        }
        catch
        {
            dbStatus = "unavailable";
        }

        var syncs = await _db.SyncStatuses
            .AsNoTracking()
            .OrderByDescending(s => s.StartedAt)
            .Take(10)
            .ToListAsync();

        var syncRows = string.Join("\n", syncs.Select(s => $@"
            <tr>
                <td>{s.Id}</td>
                <td>{s.SyncType}</td>
                <td><span class=""badge {StatusClass(s.Status)}"">{s.Status}</span></td>
                <td>{s.StartedAt:yyyy-MM-dd HH:mm:ss} UTC</td>
                <td>{s.CompletedAt?.ToString("yyyy-MM-dd HH:mm:ss") ?? "—"}</td>
                <td>+{s.ProductsAdded} ~{s.ProductsUpdated} -{s.ProductsDeleted}</td>
                <td>{s.CompatibilitiesUpdated}</td>
                <td>{(s.ErrorMessage != null ? $"<span class=\"text-danger\">{System.Net.WebUtility.HtmlEncode(s.ErrorMessage)}</span>" : "—")}</td>
            </tr>"));

        var html = $@"<!DOCTYPE html>
<html lang=""en"">
<head>
<meta charset=""UTF-8"">
<meta name=""viewport"" content=""width=device-width, initial-scale=1"">
<title>ORCA API</title>
<link rel=""stylesheet"" href=""https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"">
<style>
body {{ background: #f8f9fa; }}
.hero {{ background: #0d6efd; color: white; padding: 2rem; border-radius: 0 0 1rem 1rem; }}
.stat-card {{ border-left: 4px solid #0d6efd; }}
</style>
</head>
<body>
<div class=""hero mb-4"">
  <div class=""container"">
    <h1 class=""mb-0"">ORCA API</h1>
    <p class=""mb-0 opacity-75"">Bathroom Compatibility Finder — ASP.NET Core 8</p>
  </div>
</div>
<div class=""container"">

  <div class=""row mb-4"">
    <div class=""col-md-4"">
      <div class=""card stat-card"">
        <div class=""card-body"">
          <h6 class=""text-muted"">Products</h6>
          <h2>{productCount:N0}</h2>
        </div>
      </div>
    </div>
    <div class=""col-md-4"">
      <div class=""card stat-card"">
        <div class=""card-body"">
          <h6 class=""text-muted"">Compatibility Records</h6>
          <h2>{compatibilityCount:N0}</h2>
        </div>
      </div>
    </div>
    <div class=""col-md-4"">
      <div class=""card stat-card"">
        <div class=""card-body"">
          <h6 class=""text-muted"">Database</h6>
          <h2><span class=""badge {(dbStatus == "healthy" ? "bg-success" : "bg-danger")}"">{dbStatus}</span></h2>
        </div>
      </div>
    </div>
  </div>

  <div class=""card mb-4"">
    <div class=""card-header""><strong>API Endpoints</strong></div>
    <div class=""card-body p-0"">
      <table class=""table table-sm mb-0"">
        <thead class=""table-light""><tr><th>Method</th><th>Path</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><span class=""badge bg-success"">GET</span></td><td><a href=""/api/health"">/api/health</a></td><td>Health check + DB stats</td></tr>
          <tr><td><span class=""badge bg-success"">GET</span></td><td><a href=""/api/categories"">/api/categories</a></td><td>All product categories</td></tr>
          <tr><td><span class=""badge bg-success"">GET</span></td><td><a href=""/api/products"">/api/products</a></td><td>All products (paginated)</td></tr>
          <tr><td><span class=""badge bg-success"">GET</span></td><td>/api/product/{{sku}}</td><td>Single product by SKU</td></tr>
          <tr><td><span class=""badge bg-success"">GET</span></td><td>/api/compatible/{{sku}}</td><td>Compatible products for a SKU</td></tr>
          <tr><td><span class=""badge bg-primary"">POST</span></td><td>/api/compatibility/search</td><td>Search with filters</td></tr>
          <tr><td><span class=""badge bg-primary"">POST</span></td><td>/api/compute-compatibilities</td><td>Recompute all compatibilities</td></tr>
          <tr><td><span class=""badge bg-primary"">POST</span></td><td>/api/salsify/webhook</td><td>Salsify publication webhook</td></tr>
          <tr><td><span class=""badge bg-success"">GET</span></td><td><a href=""/api/salsify/status"">/api/salsify/status</a></td><td>Sync status history</td></tr>
          <tr><td><span class=""badge bg-primary"">POST</span></td><td>/api/salsify/cleanup</td><td>Remove old sync records</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class=""card"">
    <div class=""card-header d-flex justify-content-between align-items-center"">
      <strong>Recent Syncs</strong>
      <a href=""/api/salsify/status"" class=""btn btn-sm btn-outline-primary"">View JSON</a>
    </div>
    <div class=""card-body p-0"">
      <div class=""table-responsive"">
        <table class=""table table-sm table-hover mb-0"">
          <thead class=""table-light"">
            <tr><th>#</th><th>Type</th><th>Status</th><th>Started</th><th>Completed</th><th>Products</th><th>Compatibilities</th><th>Error</th></tr>
          </thead>
          <tbody>
            {(syncs.Count == 0 ? "<tr><td colspan=\"8\" class=\"text-center text-muted py-3\">No syncs yet</td></tr>" : syncRows)}
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div>
</body>
</html>";

        return Content(html, "text/html");
    }

    private static string StatusClass(string status) => status switch
    {
        "completed" => "bg-success",
        "running" => "bg-primary",
        "failed" => "bg-danger",
        "queued" => "bg-warning text-dark",
        _ => "bg-secondary"
    };
}
