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
    <link rel=""icon"" type=""image/png"" href=""https://res.cloudinary.com/american-bath-group/image/upload/v1628517134/abg-graphics/logos/abg/abg-logos/png/star-icon-blue.png"">
    <title>Access Restricted — ORCA</title>
    <link rel=""stylesheet"" href=""/static/css/tailwind.css"">
</head>
<body class=""bg-stone-50 min-h-screen flex items-center justify-center p-6"">
    <div class=""max-w-sm w-full text-center space-y-4"">
        <div class=""text-4xl select-none"">🔒</div>
        <h1 class=""text-xl font-semibold text-gray-900"">Access Restricted</h1>
        <p class=""text-sm text-gray-500"">
            Your email domain is not authorized to access ORCA. Access is limited to
            authorized ABG company accounts.
        </p>
        <a href=""/account/login""
           class=""inline-block mt-2 text-sm underline text-gray-400 hover:text-gray-700 transition"">
            Try a different account
        </a>
    </div>
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
