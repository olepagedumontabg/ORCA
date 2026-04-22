using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace ORCA.Api.Controllers;

[ApiController]
public class HomeController : ControllerBase
{
    private readonly IWebHostEnvironment _env;

    public HomeController(IWebHostEnvironment env)
    {
        _env = env;
    }

    private bool Auth0Enabled =>
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_DOMAIN")) &&
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_CLIENT_ID")) &&
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_CLIENT_SECRET"));

    private string TemplatesDir
    {
        get
        {
            var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "templates"));
            if (Directory.Exists(path)) return path;

            path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "templates"));
            if (Directory.Exists(path)) return path;

            path = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "templates"));
            if (Directory.Exists(path)) return path;

            return Path.GetFullPath(Path.Combine(_env.ContentRootPath, "..", "templates"));
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

    private ContentResult ServeTemplateWithUser(string filename, string userEmail)
    {
        var path = Path.Combine(TemplatesDir, filename);
        if (!System.IO.File.Exists(path))
            return Content($"<h1>404 - {filename} not found</h1>", "text/html");
        var html = System.IO.File.ReadAllText(path);
        html = html.Replace("{{USER_EMAIL}}", System.Text.Encodings.Web.HtmlEncoder.Default.Encode(userEmail));
        html = html.Replace("{{USER_SECTION_STYLE}}", "");
        return Content(html, "text/html");
    }

    private ContentResult ServeTemplatePublic(string filename)
    {
        var path = Path.Combine(TemplatesDir, filename);
        if (!System.IO.File.Exists(path))
            return Content($"<h1>404 - {filename} not found</h1>", "text/html");
        var html = System.IO.File.ReadAllText(path);
        html = html.Replace("{{USER_EMAIL}}", "");
        html = html.Replace("{{USER_SECTION_STYLE}}", "display:none");
        return Content(html, "text/html");
    }

    [HttpGet("/")]
    public ContentResult Index() => ServeTemplate("index.html");

    [HttpGet("/sync-history")]
    public ContentResult SyncHistory() => ServeTemplate("sync_history.html");

    [HttpGet("/documentation")]
    public ContentResult Documentation() => ServeTemplate("documentation.html");

    [HttpGet("/overrides")]
    public async Task<IActionResult> Overrides()
    {
        // If Auth0 is not yet configured, serve the page without any auth gate.
        if (!Auth0Enabled)
            return ServeTemplatePublic("overrides.html");

        // Unauthenticated → redirect to Auth0 login, return here afterwards
        if (User?.Identity?.IsAuthenticated != true)
        {
            var props = new AuthenticationProperties { RedirectUri = "/overrides" };
            return Challenge(props, Auth0.AspNetCore.Authentication.Auth0Constants.AuthenticationScheme);
        }

        // Authenticated but missing the required role → 403 page
        if (!User.IsInRole("override-admin"))
            return Content(System.IO.File.ReadAllText(Path.Combine(TemplatesDir, "403.html")), "text/html");

        // Authenticated + correct role → serve page with email injected
        var email = User.FindFirst(ClaimTypes.Email)?.Value
                 ?? User.FindFirst("email")?.Value
                 ?? User.Identity?.Name
                 ?? "User";

        return ServeTemplateWithUser("overrides.html", email);
    }
}
