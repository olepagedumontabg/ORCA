using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using System.Text.Encodings.Web;

namespace ORCA.Api.Controllers;

[ApiController]
public class HomeController : ControllerBase
{
    private readonly IWebHostEnvironment _env;

    private const string RoleViewer = "ORCA - Viewer";
    private const string RoleEditor = "ORCA - Editor";
    private const string RoleAdmin  = "ORCA - Admin";

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

    /// <summary>
    /// Ensures the request is authenticated and carries at least the Viewer role.
    /// Returns a Challenge (login redirect) when unauthenticated,
    /// a 403 response when the minimum role is missing, or null when access is granted.
    /// </summary>
    private IActionResult? RequireViewer(string redirectUri = "/")
    {
        if (User?.Identity?.IsAuthenticated != true)
        {
            var props = new AuthenticationProperties { RedirectUri = redirectUri };
            return Challenge(props, Auth0.AspNetCore.Authentication.Auth0Constants.AuthenticationScheme);
        }

        if (!User.IsInRole(RoleViewer) && !User.IsInRole(RoleEditor) && !User.IsInRole(RoleAdmin))
            return Serve403("You need the <strong>ORCA - Viewer</strong> role (or higher) to access this application.");

        return null;
    }

    private IActionResult Serve403(string message)
    {
        var file = Path.Combine(TemplatesDir, "403.html");
        var html = System.IO.File.ReadAllText(file);
        html = InjectRoleTokens(html);
        html = html.Replace("{{FORBIDDEN_MESSAGE}}", message);
        Response.StatusCode = 403;
        return Content(html, "text/html");
    }

    /// <summary>
    /// Resolves the authenticated user's display email.
    /// </summary>
    private string UserEmail =>
        User?.FindFirst(ClaimTypes.Email)?.Value
        ?? User?.FindFirst("email")?.Value
        ?? User?.Identity?.Name
        ?? "User";

    private bool IsEditor => User?.IsInRole(RoleEditor) == true || User?.IsInRole(RoleAdmin) == true;
    private bool IsAdmin  => User?.IsInRole(RoleAdmin)  == true;

    /// <summary>
    /// Replaces the role-visibility tokens in a template with the correct inline style
    /// for the authenticated user, so the server controls which nav links are rendered.
    /// </summary>
    private string InjectRoleTokens(string html)
    {
        html = html.Replace("{{USER_EMAIL}}", HtmlEncoder.Default.Encode(UserEmail));
        html = html.Replace("{{USER_SECTION_STYLE}}", "");
        html = html.Replace("{{STYLE_EDITOR}}", IsEditor ? "" : " style=\"display:none\"");
        html = html.Replace("{{STYLE_ADMIN}}",  IsAdmin  ? "" : " style=\"display:none\"");
        return html;
    }

    private ContentResult ServeTemplate(string filename)
    {
        var path = Path.Combine(TemplatesDir, filename);
        if (!System.IO.File.Exists(path))
            return Content($"<h1>404 - {filename} not found</h1>", "text/html");
        var html = InjectRoleTokens(System.IO.File.ReadAllText(path));
        return Content(html, "text/html");
    }

    // ── Routes ──────────────────────────────────────────────────────────────

    /// <summary>GET /  — requires ORCA - Viewer (or higher)</summary>
    [HttpGet("/")]
    public IActionResult Index()
    {
        // Check for domain restriction error BEFORE the auth check.
        // If we redirect to Auth0 here, the restriction fires again → infinite loop.
        if (Request.Query["auth_error"] == "domain_restriction")
            return ServeDomainRestriction();

        var deny = RequireViewer("/");
        if (deny != null) return deny;
        return ServeTemplate("index.html");
    }

    private IActionResult ServeDomainRestriction()
    {
        Response.StatusCode = 403;
        return Content(@"<!DOCTYPE html>
<html lang=""en"">
<head>
    <meta charset=""UTF-8"">
    <meta name=""viewport"" content=""width=device-width, initial-scale=1.0"">
    <title>Access Restricted — Bathroom Compatibility Finder</title>
    <link rel=""stylesheet"" href=""/static/css/tailwind.css"">
    <link rel=""stylesheet"" href=""https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"">
</head>
<body class=""bg-gray-50 min-h-screen flex flex-col"">
    <header class=""bg-white shadow-sm border-b border-gray-200 h-20"">
        <div class=""container mx-auto px-4 h-full flex items-center"">
            <a href=""/"" class=""flex items-center"">
                <img src=""/static/images/abg-logo-header.svg"" alt=""ABG Logo"" class=""h-6 w-auto"">
            </a>
        </div>
    </header>
    <main class=""flex-grow flex items-center justify-center"">
        <div class=""text-center max-w-md px-4"">
            <div class=""inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-100 mb-6"">
                <i class=""fas fa-ban text-red-500 text-3xl""></i>
            </div>
            <h1 class=""text-3xl font-bold text-gray-900 mb-3"">Access Restricted</h1>
            <p class=""text-gray-600 mb-2"">
                Your email address is not authorised to access this application.
            </p>
            <p class=""text-gray-400 text-sm mb-8"">
                Access is limited to ABG email domains. Contact your administrator if you believe this is an error.
            </p>
            <a href=""/account/logout""
               class=""inline-flex items-center justify-center gap-2 bg-primary hover:bg-blue-900 text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition"">
                <i class=""fas fa-sign-out-alt""></i> Sign out
            </a>
        </div>
    </main>
</body>
</html>", "text/html");
    }

    /// <summary>GET /sync-history — requires ORCA - Admin</summary>
    [HttpGet("/sync-history")]
    public IActionResult SyncHistory()
    {
        var deny = RequireViewer("/sync-history");
        if (deny != null) return deny;
        if (!IsAdmin)
            return Serve403("You need the <strong>ORCA - Admin</strong> role to view Sync History.");
        return ServeTemplate("sync_history.html");
    }

    /// <summary>GET /documentation — requires ORCA - Admin</summary>
    [HttpGet("/documentation")]
    public IActionResult Documentation()
    {
        var deny = RequireViewer("/documentation");
        if (deny != null) return deny;
        if (!IsAdmin)
            return Serve403("You need the <strong>ORCA - Admin</strong> role to view API Documentation.");
        return ServeTemplate("documentation.html");
    }

    /// <summary>GET /overrides — requires ORCA - Editor (or Admin)</summary>
    [HttpGet("/overrides")]
    public IActionResult Overrides()
    {
        var deny = RequireViewer("/overrides");
        if (deny != null) return deny;
        if (!IsEditor)
            return Serve403("You need the <strong>ORCA - Editor</strong> role (or higher) to manage Overrides.");
        return ServeTemplate("overrides.html");
    }
}
