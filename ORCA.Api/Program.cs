using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;
using ORCA.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// ---------- Database ----------
// Read DATABASE_URL from environment (standard for Replit/Neon PostgreSQL)
var databaseUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? builder.Configuration.GetConnectionString("DefaultConnection");

if (string.IsNullOrEmpty(databaseUrl))
    throw new InvalidOperationException(
        "DATABASE_URL environment variable or ConnectionStrings:DefaultConnection must be set.");

builder.Services.AddDbContext<OrcaDbContext>(options =>
    options.UseNpgsql(databaseUrl, npgsql =>
    {
        npgsql.EnableRetryOnFailure(3);
        npgsql.CommandTimeout(30);
    }));

// ---------- Services ----------
builder.Services.AddScoped<IProductService, ProductService>();
builder.Services.AddScoped<ICompatibilityService, CompatibilityService>();
builder.Services.AddScoped<ICompatibilityEngine, CompatibilityEngine>();

// ---------- Controllers ----------
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
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
// Replit sets PORT env var; default to 5000
var port = Environment.GetEnvironmentVariable("PORT") ?? "5000";
builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

var app = builder.Build();

// ---------- Middleware ----------
app.UseCors();
app.MapControllers();

// ---------- Startup info ----------
app.Logger.LogInformation("ORCA API starting on port {Port}", port);

app.Run();
