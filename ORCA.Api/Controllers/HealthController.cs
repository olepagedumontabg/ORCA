using Microsoft.AspNetCore.Mvc;
using ORCA.Api.Services.Interface;

namespace ORCA.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class HealthController : ControllerBase
{
    private readonly IHealthService _health;

    public HealthController(IHealthService health)
    {
        _health = health;
    }

    [HttpGet]
    public async Task<IActionResult> Get()
    {
        var result = await _health.GetAsync();

        if (result.Status == "healthy")
            return Ok(new
            {
                status             = result.Status,
                productCount       = result.ProductCount,
                compatibilityCount = result.CompatibilityCount,
                timestamp          = result.Timestamp
            });

        return Ok(new
        {
            status    = result.Status,
            error     = result.Error,
            timestamp = result.Timestamp
        });
    }
}
