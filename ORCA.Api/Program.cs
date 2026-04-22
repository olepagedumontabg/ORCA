using Auth0.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.FileProviders;
using ORCA.Api.Data;
using ORCA.Api.Services;
using ORCA.Api.Services.Interface;
using System.Security.Claims;

var builder = WebApplication.CreateBuilder(args);

// ---------- Database ----------
var databaseUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? builder.Configuration.GetConnectionString("DefaultConnection");

if (string.IsNullOrEmpty(databaseUrl))
    throw new InvalidOperationException(
        "DATABASE_URL environment variable or ConnectionStrings:DefaultConnection must be set.");

string connectionString;
if (databaseUrl.StartsWith("postgresql://") || databaseUrl.StartsWith("postgres://"))
{
    var uri = new Uri(databaseUrl);
    var userInfo = uri.UserInfo.Split(':');
    var host = uri.Host;
    var db = uri.AbsolutePath.TrimStart('/');
    var user = userInfo[0];
    var pass = userInfo.Length > 1 ? Uri.UnescapeDataString(userInfo[1]) : "";
    connectionString = $"Host={host};Database={db};Username={user};Password={pass};SSL Mode=Require;Trust Server Certificate=true";
}
else
{
    connectionString = databaseUrl;
}

builder.Services.AddDbContext<OrcaDbContext>(options =>
    options.UseNpgsql(connectionString, npgsql =>
    {
        npgsql.EnableRetryOnFailure(3);
        npgsql.CommandTimeout(30);
    }));

// ---------- HttpClient ----------
builder.Services.AddHttpClient<ISalsifyService, SalsifyService>(client =>
{
    client.Timeout = TimeSpan.FromMinutes(10);
});

// ---------- Services ----------
builder.Services.AddScoped<IProductService, ProductService>();
builder.Services.AddScoped<ICompatibilityService, CompatibilityService>();
builder.Services.AddScoped<ICompatibilityEngine, CompatibilityEngine>();

// ---------- Swagger ----------
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "ORCA Compatibility API",
        Version = "v1",
        Description = "Bathroom product compatibility finder — identifies compatible shower bases, bathtubs, doors, walls, screens, and more."
    });

    var xmlFile = $"{System.Reflection.Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    if (File.Exists(xmlPath))
        options.IncludeXmlComments(xmlPath);
});

// ---------- Auth0 (required — fail-closed if not configured) ----------
var auth0Domain = Environment.GetEnvironmentVariable("AUTH0_DOMAIN") ?? "";
var auth0ClientId = Environment.GetEnvironmentVariable("AUTH0_CLIENT_ID") ?? "";
var auth0ClientSecret = Environment.GetEnvironmentVariable("AUTH0_CLIENT_SECRET") ?? "";

if (string.IsNullOrEmpty(auth0Domain) || string.IsNullOrEmpty(auth0ClientId) || string.IsNullOrEmpty(auth0ClientSecret))
{
    // Fail startup hard — the Overrides section must never be unprotected.
    throw new InvalidOperationException(
        "Auth0 is required but not configured. " +
        "Set the AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET secrets " +
        "in the Replit Secrets panel before starting the application.");
}

builder.Services
    .AddAuth0WebAppAuthentication(options =>
    {
        options.Domain = auth0Domain;
        options.ClientId = auth0ClientId;
        options.ClientSecret = auth0ClientSecret;
        options.Scope = "openid profile email";

        // Map the Auth0 namespaced roles claim to ClaimTypes.Role so that
        // User.IsInRole("override-admin") works as expected.
        options.OpenIdConnectEvents = new Microsoft.AspNetCore.Authentication.OpenIdConnect.OpenIdConnectEvents
        {
            OnTicketReceived = ctx =>
            {
                var identity = ctx.Principal?.Identity as ClaimsIdentity;
                if (identity == null) return Task.CompletedTask;

                // Auth0 Post Login Action sets roles using the custom namespace:
                // https://medallion.americanbathgroup.com/roles → ["override-admin"]
                var rolesClaim = "https://medallion.americanbathgroup.com/roles";
                var rolesJson = identity.FindFirst(rolesClaim)?.Value;
                if (!string.IsNullOrEmpty(rolesJson))
                {
                    var roles = System.Text.Json.JsonSerializer.Deserialize<string[]>(rolesJson);
                    if (roles != null)
                        foreach (var role in roles)
                            identity.AddClaim(new Claim(ClaimTypes.Role, role));
                }

                return Task.CompletedTask;
            }
        };
    });

// ---------- Controllers ----------
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = ORCA.Api.SnakeCaseNamingPolicy.Instance;
        options.JsonSerializerOptions.DefaultIgnoreCondition =
            System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull;
    });

// ---------- CORS ----------
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

// ---------- Kestrel ----------
var port = Environment.GetEnvironmentVariable("PORT") ?? "5000";
builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

var app = builder.Build();

// ---------- Static files (serve /static/) ----------
var staticPath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "static"));
if (!Directory.Exists(staticPath))
    staticPath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "static"));
if (!Directory.Exists(staticPath))
    staticPath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "static"));

if (Directory.Exists(staticPath))
{
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = new PhysicalFileProvider(staticPath),
        RequestPath = "/static",
        OnPrepareResponse = ctx =>
        {
            var ext = Path.GetExtension(ctx.File.Name).ToLowerInvariant();
            if (ext is ".js" or ".css")
            {
                ctx.Context.Response.Headers["Cache-Control"] = "no-cache, must-revalidate";
            }
        }
    });
}

// ---------- Middleware ----------
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.UseSwagger();
app.UseSwaggerUI(options =>
{
    options.SwaggerEndpoint("/swagger/v1/swagger.json", "ORCA Compatibility API v1");
    options.RoutePrefix = "swagger";
});
app.MapControllers();

app.Logger.LogInformation("ORCA API starting on port {Port} with Auth0 enabled (domain: {Domain})", port, auth0Domain);

app.Run();
