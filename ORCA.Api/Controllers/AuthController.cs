using Auth0.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;

namespace ORCA.Api.Controllers;

[ApiController]
public class AuthController : ControllerBase
{
    /// <summary>
    /// GET /account/login
    /// Initiates Auth0 login flow. After successful login, the user is returned to returnUrl.
    /// </summary>
    [HttpGet("/account/login")]
    public async Task Login([FromQuery] string returnUrl = "/overrides")
    {
        // Validate returnUrl to prevent open-redirect attacks — only allow local paths
        if (string.IsNullOrEmpty(returnUrl) || !Url.IsLocalUrl(returnUrl))
            returnUrl = "/overrides";

        var authenticationProperties = new LoginAuthenticationPropertiesBuilder()
            .WithRedirectUri(returnUrl)
            .Build();

        await HttpContext.ChallengeAsync(Auth0Constants.AuthenticationScheme, authenticationProperties);
    }

    /// <summary>
    /// GET /account/logout
    /// Signs the user out locally and then redirects to Auth0 to clear the Auth0 session.
    /// </summary>
    [HttpGet("/account/logout")]
    public async Task Logout()
    {
        var authenticationProperties = new LogoutAuthenticationPropertiesBuilder()
            .WithRedirectUri("/")
            .Build();

        await HttpContext.SignOutAsync(Auth0Constants.AuthenticationScheme, authenticationProperties);
        await HttpContext.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    }

    /// <summary>
    /// GET /api/auth/me  (also available as /api/me for backward compatibility)
    /// Returns the currently authenticated user's email and roles, or 401 if not logged in.
    /// </summary>
    [HttpGet("/api/auth/me")]
    [HttpGet("/api/me")]
    public IActionResult Me()
    {
        if (User?.Identity?.IsAuthenticated != true)
            return Unauthorized(new { authenticated = false });

        var email = User.FindFirst(ClaimTypes.Email)?.Value
                 ?? User.FindFirst("email")?.Value
                 ?? User.Identity?.Name
                 ?? "Unknown";

        var roles = User.FindAll(ClaimTypes.Role).Select(c => c.Value).ToArray();

        return Ok(new
        {
            authenticated = true,
            email,
            roles,
            is_editor = roles.Contains("ORCA - Editor") || roles.Contains("ORCA - Admin"),
            is_admin  = roles.Contains("ORCA - Admin")
        });
    }
}
