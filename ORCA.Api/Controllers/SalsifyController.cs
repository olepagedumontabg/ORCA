using Microsoft.AspNetCore.Mvc;
using ORCA.Api.Services.Interface;
using System.Text.Json.Serialization;

namespace ORCA.Api.Controllers;

[ApiController]
[Route("api/salsify")]
public class SalsifyController : ControllerBase
{
    private readonly ISalsifyService _salsifyService;
    private readonly ILogger<SalsifyController> _logger;

    public SalsifyController(ISalsifyService salsifyService, ILogger<SalsifyController> logger)
    {
        _salsifyService = salsifyService;
        _logger = logger;
    }

    /// <summary>
    /// POST /api/salsify/webhook
    /// Receive a Salsify publication webhook and trigger a background data sync.
    /// Authenticate by passing the secret in the X-Salsify-Secret header.
    /// </summary>
    [HttpPost("webhook")]
    public async Task<IActionResult> Webhook(
        [FromHeader(Name = "X-Salsify-Secret")] string? key,
        [FromBody] SalsifyWebhookPayload? payload)
    {
        var webhookSecret = Environment.GetEnvironmentVariable("SALSIFY_WEBHOOK_SECRET");
        if (string.IsNullOrEmpty(webhookSecret))
        {
            _logger.LogError("SALSIFY_WEBHOOK_SECRET not configured");
            return StatusCode(500, new { success = false, error = "Webhook not configured" });
        }

        if (key != webhookSecret)
        {
            _logger.LogWarning("Invalid webhook secret from {Ip}", HttpContext.Connection.RemoteIpAddress);
            return Unauthorized(new { success = false, error = "Unauthorized" });
        }

        if (payload == null)
            return BadRequest(new { success = false, error = "No JSON payload provided" });

        _logger.LogInformation("Received Salsify webhook: {Status}", payload.PublicationStatus);

        if (payload.PublicationStatus != "completed")
        {
            return Ok(new { success = true, message = $"Ignored status: {payload.PublicationStatus}" });
        }

        var feedUrl = payload.ProductFeedUrl ?? payload.ProductFeedExportUrl;
        if (string.IsNullOrWhiteSpace(feedUrl))
            return BadRequest(new { success = false, error = "No product_feed_url in payload" });

        var result = await _salsifyService.ProcessWebhookAsync(feedUrl, payload.ChannelId, payload.ChannelName);

        return Accepted(new
        {
            success = result.Success,
            message = result.Message,
            sync_id = result.SyncId,
            status_url = $"/api/salsify/status?sync_id={result.SyncId}"
        });
    }

    /// <summary>
    /// GET /api/salsify/status?limit=10&amp;sync_id=123
    /// Get status of recent Salsify syncs.
    /// </summary>
    [HttpGet("status")]
    public async Task<IActionResult> Status(
        [FromQuery] int? sync_id,
        [FromQuery] int limit = 10)
    {
        var records = await _salsifyService.GetStatusAsync(sync_id, limit);

        if (sync_id.HasValue)
        {
            if (records.Count == 0)
                return NotFound(new { success = false, error = "Sync not found" });

            return Ok(new { success = true, sync = records[0] });
        }

        return Ok(new { success = true, syncs = records, count = records.Count });
    }

    /// <summary>
    /// POST /api/salsify/cleanup
    /// Remove old sync records.
    /// </summary>
    [HttpPost("cleanup")]
    public async Task<IActionResult> Cleanup([FromQuery] int older_than_days = 30)
    {
        var result = await _salsifyService.CleanupAsync(older_than_days);
        return Ok(new { success = result.Success, deleted = result.DeletedCount, message = result.Message });
    }
}

public class SalsifyWebhookPayload
{
    [JsonPropertyName("channel_id")]
    public string? ChannelId { get; set; }

    [JsonPropertyName("channel_name")]
    public string? ChannelName { get; set; }

    [JsonPropertyName("publication_status")]
    public string? PublicationStatus { get; set; }

    [JsonPropertyName("product_feed_url")]
    public string? ProductFeedUrl { get; set; }

    [JsonPropertyName("product_feed_export_url")]
    public string? ProductFeedExportUrl { get; set; }
}
