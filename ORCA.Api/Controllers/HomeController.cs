using Microsoft.AspNetCore.Mvc;

namespace ORCA.Api.Controllers;

[ApiController]
public class HomeController : ControllerBase
{
    private readonly IWebHostEnvironment _env;

    public HomeController(IWebHostEnvironment env)
    {
        _env = env;
    }

    private string TemplatesDir
    {
        get
        {
            var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "templates"));
            if (!Directory.Exists(path))
                path = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "templates"));
            if (!Directory.Exists(path))
                path = Path.GetFullPath(Path.Combine(_env.ContentRootPath, "..", "templates"));
            return path;
        }
    }

    private ContentResult ServeTemplate(string filename)
    {
        var path = Path.Combine(TemplatesDir, filename);
        if (!System.IO.File.Exists(path))
            return Content($"<h1>404 - {filename} not found</h1>", "text/html");
        var html = System.IO.File.ReadAllText(path);
        return Content(html, "text/html");
    }

    [HttpGet("/")]
    public ContentResult Index() => ServeTemplate("index.html");

    [HttpGet("/sync-history")]
    public ContentResult SyncHistory() => ServeTemplate("sync_history.html");

    [HttpGet("/documentation")]
    public ContentResult Documentation() => ServeTemplate("documentation.html");

    [HttpGet("/overrides")]
    public ContentResult Overrides() => ServeTemplate("overrides.html");
}
