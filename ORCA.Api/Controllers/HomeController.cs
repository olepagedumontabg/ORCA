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

    [HttpGet("/")]
    public ContentResult Index() => ServeTemplate("index.html");

    [HttpGet("/sync-history")]
    public ContentResult SyncHistory() => ServeTemplate("sync_history.html");

    [HttpGet("/documentation")]
    public ContentResult Documentation() => ServeTemplate("documentation.html");

    /// <summary>
    /// GET /overrides
    /// Protected: requires Auth0 login + the 'override-admin' role.
    /// Unauthenticated users are redirected to Auth0.
    /// Authenticated users without the role see a 403 page.
    /// </summary>
    [HttpGet("/overrides")]
    public IActionResult Overrides()
    {
        // Unauthenticated → redirect to Auth0 login, returning here afterwards
        if (User?.Identity?.IsAuthenticated != true)
        {
            var props = new AuthenticationProperties { RedirectUri = "/overrides" };
            return Challenge(props, Auth0.AspNetCore.Authentication.Auth0Constants.AuthenticationScheme);
        }

        // Authenticated but missing the required role → 403 page
        if (!User.IsInRole("override-admin"))
        {
            Response.StatusCode = 403;
            return Content(System.IO.File.ReadAllText(Path.Combine(TemplatesDir, "403.html")), "text/html");
        }

        // Authenticated + correct role → serve page with user email injected
        var email = User.FindFirst(ClaimTypes.Email)?.Value
                 ?? User.FindFirst("email")?.Value
                 ?? User.Identity?.Name
                 ?? "User";

        return ServeTemplateWithUser("overrides.html", email);
    }
}
