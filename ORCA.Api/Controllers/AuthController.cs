using Auth0.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace ORCA.Api.Controllers;

[ApiController]
public class AuthController : ControllerBase
{
    private readonly IConfiguration _config;

    public AuthController(IConfiguration config)
    {
        _config = config;
    }

    private bool Auth0Enabled =>
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_DOMAIN")) &&
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_CLIENT_ID")) &&
        !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AUTH0_CLIENT_SECRET"));

    /// <summary>
    /// GET /account/login
    /// Initiates Auth0 login flow, returning the user to returnUrl after success.
    /// </summary>
    [HttpGet("/account/login")]
    public async Task Login([FromQuery] string returnUrl = "/overrides")
    {
        if (!Auth0Enabled)
        {
            Response.Redirect("/");
            return;
        }

        var authenticationProperties = new LoginAuthenticationPropertiesBuilder()
            .WithRedirectUri(returnUrl)
            .Build();

        await HttpContext.ChallengeAsync(Auth0Constants.AuthenticationScheme, authenticationProperties);
    }

    /// <summary>
    /// GET /account/logout
    /// Signs the user out locally and then from Auth0.
    /// </summary>
    [HttpGet("/account/logout")]
    public async Task Logout()
    {
        if (!Auth0Enabled)
        {
            Response.Redirect("/");
            return;
        }

        var authenticationProperties = new LogoutAuthenticationPropertiesBuilder()
            .WithRedirectUri("/")
            .Build();

        await HttpContext.SignOutAsync(Auth0Constants.AuthenticationScheme, authenticationProperties);
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    }

    /// <summary>
    /// GET /api/me
    /// Returns basic info about the currently authenticated user, or 401 if not logged in.
    /// </summary>
    [HttpGet("/api/me")]
    public IActionResult Me()
    {
        if (User?.Identity?.IsAuthenticated != true)
            return Unauthorized(new { authenticated = false });

        var email = User.FindFirst(ClaimTypes.Email)?.Value
                 ?? User.FindFirst("email")?.Value
                 ?? User.Identity.Name
                 ?? "Unknown";

        var roles = User.FindAll(ClaimTypes.Role).Select(c => c.Value).ToArray();

        return Ok(new
        {
            authenticated = true,
            email,
            roles,
            is_override_admin = roles.Contains("override-admin")
        });
    }
}
