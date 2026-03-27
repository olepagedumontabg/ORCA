using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ORCA.Api.Data;

namespace ORCA.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class HealthController : ControllerBase
{
    private readonly OrcaDbContext _db;

    public HealthController(OrcaDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<IActionResult> Get()
    {
        try
        {
            var productCount = await _db.Products.CountAsync();
            var compatibilityCount = await _db.ProductCompatibilities.CountAsync();

            return Ok(new
            {
                status = "healthy",
                productCount,
                compatibilityCount,
                timestamp = DateTime.UtcNow
            });
        }
        catch (Exception ex)
        {
            return Ok(new
            {
                status = "unhealthy",
                error = ex.Message,
                timestamp = DateTime.UtcNow
            });
        }
    }
}
